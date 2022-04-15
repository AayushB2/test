"""
RuViz - data module
Version: Themis 1.1.0

Provides a basis for storing data as csv, either event based or continuous.

*******************************************************************************

Copyright (c) 2016 Erik van den Berge, Radboud University

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""

import viz, csv, time, utils

_datafolder = utils.getPath('data')

class _AbstractLogger(viz.EventClass):
    def __init__(self, filename, path=_datafolder, delimiter=';'):
        viz.EventClass.__init__(self)

        self.init_time = viz.tick()
        timestamp = time.strftime('%Y%m%d%H%M', time.localtime())

        f = '{0}\\{1}_{2}.csv'.format(path,filename,timestamp)
        self.file = open(f, 'wb')
        self.writer = csv.writer(self.file,delimiter=delimiter)

    def getElapsedTime(self,precision=3):
        e = viz.tick() - self.init_time
        result = round(e,int(precision))
        return result

    def getLocalTime(self):
        result = time.strftime('%H:%M:%S', time.localtime())
        return result

    def _write(self, *args):
        datarow = []
        for a in args:
            data = a if isinstance(a,(list,tuple)) else [a]
            datarow.extend(data)
        self.writer.writerow(datarow)


class EventLogger(_AbstractLogger):
    def __init__(self,filename,**kwargs):
        _AbstractLogger.__init__(self,filename,**kwargs)

        self.callback(viz.INIT_EVENT, self.onInit)
        self.callback(viz.EXIT_EVENT, self.onExit)

    def log(self, *args):
        base = [self.getElapsedTime(), self.getLocalTime()]
        self._write(base,*args)

    def logHeader(self, *args):
        base = ['elapsed', 'local-time','event']
        self._write(base, *args)

    def onInit(self):
        self.log('initialize')

    def onExit(self):
        self.log('exit')
        self.file.close()


class ContinuousLogger(_AbstractLogger):
    def __init__(self,filename,rate,**kwargs):
        _AbstractLogger.__init__(self,filename,**kwargs)

        self.rate = float(1 / rate) #Hz to ms
        self.recording = False;

        self.callback(viz.TIMER_EVENT, self.onTimer)
        self.callback(viz.EXIT_EVENT, self.onExit)

    def log(self,*args):
        base = self.getElapsedTime()
        self._write(base,*args)

    def logHeader(self,*args):
        base = 'elapsed'
        self._write(base,*args)

    def onTimer(self,t):
        pass

    def onStart(self):
        if not self.recording:
            self.recording = True
            self.starttimer(0, self.rate, viz.FOREVER)

    def onStop(self):
        if self.recording:
            self.killtimer(0)
            self.recording = False

    def onExit(self):
        self.file.close()
