"""
RuViz - display module
Version: Hecate 1.0.2

Window and display management.
Tested with Vizard v4 and v5.

TODO: Easy setup for defaults (currently hardcoded)

*******************************************************************************

Copyright (c) 2016 Erik van den Berge, Radboud University

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""

import viz

monitors = viz.window.getMonitorList()
windows = {}

def extend(main,view=None):
    x_offset = 0
    y_offset = 0

    """
    Vizard uses the bottom-left corner of the fullscreen boundrybox as its
    origin for screen-space translations, while the OS uses the top-left
    corner of the primary monitor. The latter is a more intuitive coordinate
    system for positioning new windows, so let's offset Vizard's origin to
    match the OS's.
    """

    # Find primary monitor for OS origin
    for m in monitors:
        if m.primary:
            y_offset = m.size[1]
        pass

    # Find corner of fullscreen bounding box (Vizard origin)
    for m in monitors:
        if m.position[0] < x_offset:
            x_offset = m.position[0]
        max_y = m.size[1] + m.position[1]
        if max_y > y_offset:
            y_offset = max_y
    origin = [-x_offset, y_offset]

    # Create all windows, matching each monitor position and resolution
    for m in monitors:
        wx = origin[0] + m.position[0]
        wy = origin[1] - m.position[1]
        if m.id == main:
            viz.MainWindow.setSize(m.size, mode=viz.WINDOW_PIXELS)
            viz.MainWindow.setPosition(wx,wy,mode=viz.WINDOW_PIXELS)
            nw = viz.MainWindow
        else:
            if view:
                nv = view[m.id] if isinstance(view, list) else view
            else:
                nv = viz.addView()
            nw = viz.addWindow()
            nw.setSize(m.size, mode=viz.WINDOW_PIXELS)
            nw.setPosition(wx,wy,mode=viz.WINDOW_PIXELS)
            nw.setView(nv)
            # Defaults
            nw.fov(65)
            nv.getHeadLight().disable()
            viz.link(viz.MainView, nv)
        windows[m.id] = nw

def getWindow(id):
    try:
        return windows[id]
    except:
        viz.logError('** ERROR: Could not find window on monitor ID {}'.format(id))
        return None

