"""
RuViz - utils module
Version: Gaia 1.0.7

Collection of functions that will make your life a lot easier when coding in Vizard v4 or v5.
Config implementation was inspired by idTech engine games.

*******************************************************************************

Copyright (c) 2016 Erik van den Berge, Radboud University
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""

import viz, os, re, shlex

""" GENERAL """

def init():
    viz.MainView.getHeadLight().disable()        # Disables default light
    viz.mouse.setVisible(False)                    # Hides cursor
    viz.setMultiSample(8)                        # Anti-aliasing
    viz.setOption('viz.glFinish',1)                # Solution to some common bugs

def getPath(*args):
    # Returns absolute path for project root or specified folder, regardless of publishing status
    p = os.pardir if args else os.curdir
    r = os.path.join(viz.getOption('viz.publish.path',''), p)
    return os.path.abspath(os.path.join(r, *args))

""" RESOURCES """

_resfolder = getPath('res')

def _setResource(path):
    viz.res.addPath(path)
    viz.res.addPublishDirectory(path)

def setRes(dir=_resfolder, subdirs=[]):
    if subdirs is None:
        _setResource(dir)
    else:
        if not subdirs:
            subdirs = [d[0] for d in os.walk(dir)]
        for subdir in subdirs:
            _setResource(os.path.join(dir, subdir))


""" PUBLISH """

_pubset = {
    'viz.publish.load_message' : 'Loading...',
    'viz.publish.load_title' : '',
    'viz.publish.company' : 'Radboud University',
    }

def setPublish(options={}):
    _pubset.update(options)
    for s in _pubset:
        viz.setOption(s,_pubset[s])


""" KEY CONVERTER """

KEY_LOOKUP_TABLE = {
    'SPACE'        :' ',
    'BACKSPACE'    :'65288',
    'TAB'        :'65289',
    'RETURN'    :'65293',
    'ESCAPE'    :'65307',
    'HOME'        :'65360',
    'LEFTARROW'    :'65361',
    'UPARROW'    :'65362',
    'RIGHTARROW':'65363',
    'DOWNARROW'    :'65364',
    'PGUP'        :'65365',
    'PGDN'        :'65366',
    'END'        :'65367',
    'INS'        :'65379',
    'KP_ENTER'    :'65421',
    '*'            :'65450',
    'KP_PLUS'    :'65451',
    'KP_MINUS'    :'65453',
    'KP_DEL'    :'65454',
    'KP_SLASH'    :'65455',
    'KP_0'        :'65456',
    'KP_1'        :'65457',
    'KP_2'        :'65458',
    'KP_3'        :'65459',
    'KP_4'        :'65460',
    'KP_5'        :'65461',
    'KP_6'        :'65462',
    'KP_7'        :'65463',
    'KP_8'        :'65464',
    'KP_9'        :'65465',
    'F1'        :'65470',
    'F2'        :'65471',
    'F3'        :'65472',
    'F4'        :'65473',
    'F5'        :'65474',
    'F6'        :'65475',
    'F7'        :'65476',
    'F8'        :'65477',
    'F9'        :'65478',
    'F10'        :'65479',
    'F11'        :'65480',
    'F12'        :'65481',
    'SHIFT'        :'65505',
    'RSHIFT'    :'65506',
    'CTRL'        :'65507',
    'RCTRL'        :'65508',
    'CAPSLOCK'    :'65509',
    'ALT'        :'65513',
    'RALT'        :'65514',
    'DEL'        :'65535'
    }

def getKeyName(key):
    for i, c in KEY_LOOKUP_TABLE.iteritems():
        if c == key:
            return i
    return key

def getKeyCode(key):
    k = key.upper()
    return KEY_LOOKUP_TABLE[k] if k in KEY_LOOKUP_TABLE else key


""" CONFIG """

_cfgfolder = getPath('cfg')

class Config():
    def __init__(self, dir=_cfgfolder, profile=[]):
        self.cfg = {}
        self.dir = dir
        self.load(dir,profile)

    def _loadConfig(self, path):
        try:
            cf = open(path, 'r')
            cl = cf.readlines()
            cf.close()
        except IOError:
            raise
        else:
            for i, c in enumerate(cl):
                s = shlex.split(c)[:3] if not c.startswith('//') else []
                if len(s):
                    if s[0] == 'bind':
                        self.cfg[s[2]] = getKeyCode(s[1])
                    elif s[0] == 'seta':
                        self.cfg[s[1]] = s[2]
                    else:
                        viz.logWarn('** WARNING: CFG Read Error in line {}'.format(i+1))


    def load(self, dir, profile):
        profiles = [profile] if not isinstance(profile, (list,tuple)) else profile
        if profiles:
            paths = ['{}.cfg'.format(p) for p in profiles]
        else:
            paths = [f for f in os.listdir(dir) if f.endswith('.cfg')]
        for p in paths:
            try:
                self._loadConfig('\\'.join([dir,p]))
            except:
                viz.logWarn('** WARNING: Failed to load file {}'.format(p))

    def _convert(self,raw,type):
        if type == 'bool':
            trues = ['true', '1', 'yes']
            return True if raw.lower() in trues else False
        elif type == 'int':
            return int(raw)
        elif type == 'float':
            return float(raw)
        elif type == 'str':
            return str(raw)
        elif type == 'list':
            return [l.lstrip(' ').rstrip(' ') for l in re.split(';|,',raw)]
        else:
            return raw

    def get(self, item, *args):
        # get value from config, as predefined type (optional) and subtype (optional, if type is list). Default type is string.
        try:
            raw = self.cfg[item]
            t = args[0] if args else ''
            output = self._convert(raw,t)
            if t == 'list' and len(args) > 1:
                st = args[1]
                for i, sr in enumerate(output):
                    output[i] = self._convert(sr,st)
            return output

        except KeyError:
            viz.logError('** ERROR: "{}" not found in config'.format(item))
            return None
