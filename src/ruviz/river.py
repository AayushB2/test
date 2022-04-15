"""
RuViz - river module
Version: Charon 1.1.1

For use in Radboud Immersive Virtual Environment Research lab.
Use with Worldviz Vizard 4 or later.

*******************************************************************************

Copyright (c) 2016 Erik van den Berge, Radboud University

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""

import viz, oculus, steamvr

_riverset = {
    'ip' : '192.168.1.101',        # IP address of VRPN Server
    'pos' : [1,-2,3],            # Flip positional Y axis
    'quat': [-1,2,-3,4]            # Invert orientation quaternions
    }

class Dtrack:
    def __init__(self, numtrackers=1, settings={}, linkview=True):
        _riverset.update(settings)
        VRPN_IP = 'DTrack@' + _riverset['ip']
        SWAP_POS = _riverset['pos']
        SWAP_QUAT = _riverset['quat']

        self.vrpn = viz.add('vrpn7.dle')
        self.trackers = []
        self.links = {}
        for i in range(0, numtrackers):
            self.trackers.append(self.vrpn.addTracker(VRPN_IP, i))
            self.trackers[i].swapPos(SWAP_POS)
            self.trackers[i].swapQuat(SWAP_QUAT)
        if linkview:
            viz.eyeheight(0)
            self.addLink(0,viz.MainView)

    def addLink(self, tracker, child, **kwargs):
        try:
            link = viz.link(self.trackers[tracker], child , **kwargs)
            self.links[tracker] = link
            return link
        except:
            viz.logWarn("** ERROR: invalid tracker id")

    def removeLink(self, tracker):
        try:
            self.links[tracker].remove()
            self.links[tracker] = None
        except:
            viz.logWarn("** ERROR: invalid tracker id")


class Oculus:
    def __init__(self, node=viz.MainView, autoDetectMonitor=False, **kwargs):
        self.hmd = oculus.Rift(autoDetectMonitor=autoDetectMonitor, **kwargs)
        self.sensor = self.hmd.getSensor()
        if node != None:
            viz.link(self.hmd.getSensor(),node)

    def getHMD(self):
        return self.hmd

    def getSensor(self):
        return self.sensor

    def reset(self):
        self.sensor.reset()
        return True

    def forceExtend(self):
        self.hmd.setRenderMode(oculus.RENDER_CLIENT)

class Vive:
    def __init__(self, node=viz.MainView):
        self.hmd = steamvr.HMD()
        if not self.hmd.getSensor():
            viz.logError('**ERROR: Steam VR HMD not detected!')
        else:
            self.transport = viz.addGroup()
            if node != None:
                self.viewLink = viz.link(self.transport,node)
                self.viewLink.preMultLinkable(self.hmd.getSensor())

    def getControllers(self,model=True):
        self.controllers = []
        for controller in steamvr.getControllerList():
            self.controllers.append(controller)
            if model:
                controller.model = controller.addModel(parent=self.transport)
                controller.model.disable(viz.INTERSECTION)
                viz.link(controller,controller.model)
        return self.controllers
