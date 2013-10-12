import serial
import re
import wx
import numpy
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

class DataLoggerWindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, "YoDAQ", (100,100), (640,480))

        self.SetBackgroundColour('#ece9d8')

        # Flag variables
        self.isLogging = False

        self.r = re.compile('\d* \d*\r\n')
        # Create data buffers
        self.N = 1000
        self.n = range(self.N)
        self.t = numpy.ones(self.N)
        self.x = numpy.ones(self.N)

        # Create plot area and axes
        self.fig = Figure(facecolor='#ece9d8')
        self.canvas = FigureCanvasWxAgg(self, -1, self.fig)
        self.canvas.SetPosition((0,0))
        self.canvas.SetSize((640,320))
        self.ax = self.fig.add_axes([0.08,0.1,0.86,0.8])
        self.ax.autoscale(False)
        self.ax.set_xlim(0, 1)
        self.ax.set_ylim(-.5, .5)
        self.ax.plot(self.t,self.x)

        # Create text box for event logging
        self.log_text = wx.TextCtrl(
            self, -1, pos=(140,320), size=(465,100),
            style=wx.TE_MULTILINE)
        self.log_text.SetFont(
            wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False))

        # Create timer to read incoming data and scroll plot
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.GetSample, self.timer)

        # Create start/stop button
        self.start_stop_button = wx.Button(
            self, label="Start", pos=(25,320), size=(100,100))
        self.start_stop_button.SetFont(
            wx.Font(14, wx.DEFAULT, wx.NORMAL, wx.NORMAL, False))
        self.start_stop_button.Bind(
            wx.EVT_BUTTON, self.onStartStopButton)

    def GetSample(self, event=None):
        # Get a line of text from the serial port
        while self.ser.inWaiting() > 0:
            sample_string = self.ser.readline()

            if self.r.match(sample_string):
                # Add the line to the log text box
                self.log_text.AppendText(sample_string)

                # If the line is the right length, parse it
                sample_values = sample_string[0:-2].split()

                self.t[0:self.N-1] = self.t[1:]
                self.t[self.N-1] =float(sample_values[0])/1e6
                self.x[0:self.N-1] = self.x[1:]
                self.x[self.N-1] = 3.3*float(sample_values[1])/4096 - 1.65

        # Update plot
        self.ax.cla()
        self.ax.autoscale(False)
        self.ax.set_xlim(self.t[0], self.t[-1])
        self.ax.set_ylim(-.5, .5)
        self.ax.hlines(0, self.t[0], self.t[-1], colors='r')
        self.ax.plot(self.t, self.x)
        self.canvas.draw()

    def onStartStopButton(self, event):
        if not self.isLogging:
            self.isLogging = True
            self.ser = serial.Serial()
            self.ser.baudrate = 115200
            self.ser.timeout=0.25
            self.ser.port = '/dev/ttyACM0'
            self.ser.open()
            if self.ser.isOpen():
                # We successfully opened a port, so start
                # a timer to read incoming data
                self.timer.Start(100)
                self.start_stop_button.SetLabel("Stop")
        else:
            self.timer.Stop()
            self.ser.close()
            self.isLogging = False
            self.start_stop_button.SetLabel("Start")

if __name__ == '__main__':
    app = wx.PySimpleApp()
    window = DataLoggerWindow()

    window.Show()
    app.MainLoop()
