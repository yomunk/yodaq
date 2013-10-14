import serial
import re
import wx
import numpy as np
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

class YoDAQwindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, "yodaq", (100,100), (640,480))

        self.SetBackgroundColour('#ece9d8')

        self.ser = serial.Serial()
        self.ser.baudrate = 115200
        self.ser.timeout=0.25
        self.ser.port = '/dev/ttyACM0'
        try:
            self.ser.open()
        except:
            pass
        self.isLogging = False

        self.line_format = re.compile('T: \d*( : A\d: \d*)+')
        self.time_format = re.compile('T: \d*')
        self.sample_format = re.compile('A\d: \d*')

        # Create data buffers
        self.data = []

        self.resolution = 12
        self.vref = 3.3
        self.window = 2.0

        # Create plot area and axes
        self.fig = Figure(facecolor='#ece9d8')
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetPosition((0,0))
        self.canvas.SetSize((640,320))
        self.ax = self.fig.add_axes([0.08,0.1,0.86,0.8])
        self.ax.set_xlabel('Time (s)')
        self.ax.set_ylabel('Voltage (V)')
        #self.ax.autoscale(False)
        self.ax.set_xlim(0, self.window)
        self.ax.set_ylim(0, self.vref)
        #self.ax.plot(self.t,self.x)

        self.cid = self.canvas.mpl_connect('button_press_event', self.onClick)

        # Create text box for event logging
        self.log_text = wx.TextCtrl(
            self, -1, pos=(140,350), size=(465,70),
            style=wx.TE_MULTILINE)
        self.log_text.SetFont(
            wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False))

        # Create timer to read incoming data and scroll plot
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.readSerial, self.timer)

        # Create start/stop button
        self.start_stop_button = wx.Button(
            self, label="Start", pos=(25,350), size=(100,70))
        self.start_stop_button.SetFont(
            wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False))
        self.start_stop_button.Bind(
            wx.EVT_BUTTON, self.onStartStopButton)

    def readSerial(self, event=None):
        while self.ser.inWaiting() > 0:
            line_data = self.ser.readline()

            if self.line_format.match(line_data):
                x = []
                t_match = self.time_format.match(line_data).group()
                x.append(float(t_match.split()[1]) / 1e6)
                for a_match in self.sample_format.findall(line_data):
                    x.append(self.vref*float(a_match.split()[1])/(2**self.resolution))

                self.data.append(x)

        self.data_array = np.array(self.data)
        #print self.data_array.shape

        # Update plot
        if self.data_array.shape[0] > 0:
            self.ax.cla()
            self.ax.autoscale(False)
            self.ax.set_ylim(0, self.vref)

            for i in range(1, self.data_array.shape[1]):
                self.ax.plot(self.data_array[:,0], self.data_array[:,i])

            self.ax.set_xlabel('Time (s)')
            self.ax.set_ylabel('Voltage (V)')

            last_t = self.data_array[-1,0]
            if last_t < self.window:
                self.ax.set_xlim(0, self.window)
            else:
                self.ax.set_xlim(last_t-self.window, last_t)

            self.ax.hlines(self.vref/2, self.ax.axis()[0], self.ax.axis()[1], colors='r')

            self.canvas.draw()

    def onClick(self, event):
        # Add the line to the log text box
        self.log_text.AppendText('X: {:.3f}\tY: {:.3f}\n'.format(event.xdata, event.ydata))

    def onStartStopButton(self, event):
        if not self.isLogging:
            self.isLogging = True
            self.data = []
            if self.ser.isOpen():
                self.ser.flushInput()
                self.ser.write('CMD I1 D100')
                self.timer.Start(500)
                self.start_stop_button.SetLabel("Stop")
        else:
            self.isLogging=False
            self.ser.write(' ')
            self.timer.Stop()
            self.start_stop_button.SetLabel("Start")

    def OnClose(self, event):
        self.ser.close()
        self.Destroy()

if __name__ == '__main__':
    app = wx.PySimpleApp()
    window = YoDAQwindow()

    window.Show()
    app.MainLoop()
