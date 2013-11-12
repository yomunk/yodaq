#!/usr/bin/env python2

import sys
import os
import serial
import re
import wx
import numpy as np
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.backends.backend_wxagg import NavigationToolbar2Wx as Toolbar

from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from matplotlib.patches import Rectangle

BUFFER_SIZE=100000
N_CHANS=1

class YoDAQwindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, "yodaq", (100,100), (1024,800))

        self.SetBackgroundColour('#ece9d8')

        self.ser = serial.Serial()
        self.ser.baudrate = 115200
        self.ser.timeout=0.25
        self.ser.port = '/dev/ttyACM0'
        self.ser.open()
        self.isLogging = False

        self.line_format = re.compile('T: \d*( : A\d: \d*)+')
        self.time_format = re.compile('T: \d*')
        self.sample_format = re.compile('A\d: \d*')

        # Create data buffers
        self.data = np.nan * np.ones((BUFFER_SIZE,N_CHANS+1))
        self.i = 0

        self.resolution = 12
        self.vref = 3.3
        self.vmax = 3.3
	self.vmin = 0
        self.window = 2.0

        # Create plot area and axes
        self.fig = Figure(facecolor='#ece9d8')
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetPosition((0,0))
        self.canvas.SetSize((1024,700))
        self.ax = self.fig.add_axes([0.08,0.35,0.86,0.6])
        self.ax.set_ylabel('Voltage (V)')
        self.ax.set_xlim(0, self.window)
        self.ax.set_ylim(0, self.vref)

        self.scrub_ax = self.fig.add_axes([0.08,0.1,0.86,0.2])
        self.scrub_ax.set_ylabel('Voltage (V)')
        self.scrub_ax.set_xlabel('Time (s)')

        # Create timer to read incoming data and scroll plot
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.read_serial, self.timer)

        self.create_menu()
        self.create_status_bar()

        self.toolbar = Toolbar(self.canvas)
        self.toolbar.Realize()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas,1,wx.EXPAND)
        sizer.Add(self.toolbar, 0 , wx.LEFT | wx.EXPAND)
        self.SetSizer(sizer)

    def create_menu(self):
        self.menubar = wx.MenuBar()

        menu_file = wx.Menu()
        m_save = menu_file.Append(-1, "&Save\tCtrl-S", "Save Data")
        m_exit = menu_file.Append(-1, "E&xit\tCtrl-X", "Exit")
        self.Bind(wx.EVT_MENU, self.on_save, m_save)
        self.Bind(wx.EVT_MENU, self.OnClose, m_exit)

        menu_data = wx.Menu()
        m_start_stop = menu_data.Append(-1, "&Start/Stop\tSpace", "Start/Stop data acquisition")
        m_calc_mean = menu_data.Append(-1, "Get Statistics\ts", "Compute statistics for main window")
        self.Bind(wx.EVT_MENU, self.on_start_stop, m_start_stop)
        self.Bind(wx.EVT_MENU, self.on_compute_stats, m_calc_mean)

        self.menubar.Append(menu_file, "&File")
        self.menubar.Append(menu_data, "&Data")
        self.SetMenuBar(self.menubar)

    def create_status_bar(self):
        self.statusbar = self.CreateStatusBar()

    def read_serial(self, event=None):
        while self.ser.inWaiting() > 0:
            line_data = self.ser.readline()

            if self.line_format.match(line_data):
                t_match = self.time_format.match(line_data).group()

                rawchans = self.sample_format.findall(line_data)
                chanlist = [self.vref*float(x.split()[1])/(2**self.resolution)
                        for x in rawchans]

                if len(chanlist)==N_CHANS:
                    self.data[self.i, 0] = float(t_match.split()[1]) / 1e3
                    self.data[self.i, 1:] = chanlist
                    self.i+=1

        # Update plot
        self.ax.cla()
        self.ax.autoscale(False)
        self.ax.set_ylim(self.vmin, self.vmax)

        self.scrub_ax.cla()
        self.scrub_ax.set_ylim(self.vmin, self.vmax)

        for i in range(1, self.data.shape[1]):
            self.ax.plot(self.data[:,0], self.data[:,i])
            self.scrub_ax.plot(self.data[:,0], self.data[:,i])

        self.ax.set_ylabel('Voltage (V)')
        self.scrub_ax.set_ylabel('Voltage (V)')
        self.scrub_ax.set_xlabel('Time (s)')

        last_t = self.data[self.i-1,0]
        if last_t < self.window or np.isnan(last_t):
            self.ax.set_xlim(0, self.window)
        else:
            self.ax.set_xlim(last_t-self.window, last_t)

        self.scrub_ax.set_xlim(0, last_t)

        self.ax.hlines(self.vref/2, 0, last_t, colors='r')
        self.scrub_ax.hlines(self.vref/2, 0, last_t, colors='r')

        self.canvas.draw()

    def on_start_stop(self, event):
        if not self.isLogging:
            self.isLogging = True
            self.data *= np.nan
            if self.ser.isOpen():
                self.ser.flushInput()
                self.ser.write('CMD I1 D10')
                self.timer.Start(500)
        else:
            self.isLogging=False
            self.ser.write(' ')
            self.timer.Stop()

    def on_compute_stats(self, event):
        t_min, t_max, y_min, y_max = self.ax.axis()
        data = self.data[~np.isnan(self.data).any(1)]
        data = data.compress(data[:,0]>t_min, axis=0)
        data = data.compress(data[:,0]<t_max, axis=0)

        wx.MessageBox('Min:\t\t{:.03f}\nMean:\t{:.03f}\nMax:\t{:.03f}\nSD:\t\t{:.03f}'.format(
            np.min(data[:,1]),
            np.mean(data[:,1]),
            np.max(data[:,1]),
            np.std(data[:,1]) ),
            'Statistics', wx.OK, self)

    def on_save(self, event):
        dlg = wx.FileDialog(self, "Save data as...",
                os.getcwd(),
                style=wx.SAVE | wx.OVERWRITE_PROMPT)

        if dlg.ShowModal()==wx.ID_OK:
            filename=dlg.GetPath()
            if not os.path.splitext(filename)[1]:
                filename=filename+'.txt'
            np.savetxt(filename, self.data[~np.isnan(self.data).any(1)])

        dlg.Destroy()


    def OnClose(self, event):
        self.ser.close()
        self.Destroy()

if __name__ == '__main__':
    app = wx.PySimpleApp()
    window = YoDAQwindow()

    window.Show()
    app.MainLoop()
