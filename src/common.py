"""
Dream Cafe - Common module
Version: 0.1.3
Date: 2017-04-12
Author: Erik van den Berge <e.vandenberge@ru.nl>

*******************************************************************************

The common module should contain all assets and constants that are shared across the other modules. Common is a passive module, so it cannot be run on its own and it cannot make any decisions.

Todo: should find better descriptions for objects (node3d) and items (Object class)

"""

import viz, vizact, vizshape
import math
from ruviz import utils

utils.init() # Load default settings

"""
Config & Defaults
"""

cfg = utils.Config() # Load config

KEY_START = cfg.get('start')
KEY_GRAVITY = cfg.get('gravity')
KEY_SHUFFLE = cfg.get('shuffle')
KEY_CUSTOMER = cfg.get('customer')
KEY_CLOCK = cfg.get('time')
KEY_BINMOVE = cfg.get('binmove')
KEY_STARE = cfg.get('stare')
KEY_MANNEQUIN = cfg.get('mannequin')
KEY_CANCEL = cfg.get('cancel')
KEY_WASTE = cfg.get('junk')
KEY_POSTER = cfg.get('poster')

VIVE = cfg.get('g_vive', 'bool')
VIVE_OFFSET = cfg.get('g_viveoffset','list','float') #Standing:[0,0,5.8]#R2 Vive:[1.45,0,4.5]
VIVE_ORI = [cfg.get('g_viveori','float'), 0, 0]
DEBUG = cfg.get('d_debug', 'bool')

HANDPHYSICS = cfg.get('g_handphysics', 'bool')
CLOCK_TYPE = cfg.get('r_clock','str')
ORDER_TIME = cfg.get('t_order','int')
EXPIRATION_TIME = cfg.get('t_expiration','int')
CONSUMPTION_TIME = cfg.get('t_consumption','list','int') #range
CLEANUP_TIME = cfg.get('t_cleanup', 'int')
CLEARSEAT_TIME = cfg.get('t_clearseat', 'int')
AUTO_EVENT_TIME = cfg.get('t_autoevent','list','int') #range
AUTO_CUST_TIME = cfg.get('t_autocustomer','list','int') #range
AUTO_WASTE_TIME = cfg.get('t_autowaste','list','int') #range

AUTO_EVENTS = cfg.get('g_autoevents', 'list', 'str')

MAX_WAITING_CUSTOMERS = 4
SLEEP = 6 #frames

GRAVITY = [0,-9.81,0]
ZEROG = [0.0, 0.0, 0.0]
TRAY_REQUEST_SIZE = 2

itemRegistry = {}
dynamicItems = []
targetItems = []

spawns = {
    'order' : [-.4,1.0,6.3],        #xyz global
    'bin' : [                       #xyzrp global
        [.18,0,6.5,-20,0],
        [.18,2.75,6.5,0,180],
        [2.8,0,3.3,0,0],
        [0.8,2.75,3.3,0,180],
        [2.8,0,5.7,0,0],
        [2.8,2.75,4.4,0,180]
        ],
    'card' : {                      #xyz global
        '1' : [0.778,0.835,3.916],
        '2' : [0.778,0.835,1.684],
        '3' : [2.838,0.835,3.927],
        '4' : [2.837,0.835,1.684]
        }
    }

materialProperties = {
    'default' : {
        'bounce' : 0.2,
        'density' : 0.4,
        'friction' : 0.8,
        'hardness' : 0.2
        }
    }

"""
Event Handlers
"""

START_EVENT = viz.getEventID('START_EVENT')
DISCARD_EVENT = viz.getEventID('DISCARD_EVENT')
ORDER_EVENT = viz.getEventID('ORDER_EVENT')
ASSEMBLE_EVENT = viz.getEventID('ASSEMBLE_EVENT')
DELIVER_EVENT = viz.getEventID('DELIVER_EVENT')
EXPIRE_EVENT = viz.getEventID('EXPIRE_EVENT')
GARBAGE_EVENT = viz.getEventID('GARBAGE_EVENT')
CUSTOMER_ENTER_EVENT = viz.getEventID('CUSTOMER_ENTER_EVENT')
CUSTOMER_LEAVE_EVENT = viz.getEventID('CUSTOMER_LEAVE_EVENT')
GRAVITY_EVENT = viz.getEventID('GRAVITY_EVENT')
OBJECT_ZEROG_EVENT = viz.getEventID('OBJECT_ZEROG_EVENT')
SHUFFLE_CARDS_EVENT = viz.getEventID('SHUFFLE_CARDS_EVENT')
CLOCK_EVENT = viz.getEventID('CLOCK_EVENT')
BIN_EVENT = viz.getEventID('BIN_EVENT')
STARE_EVENT = viz.getEventID('STARE_EVENT')
MANNEQUIN_EVENT = viz.getEventID('MANNEQUIN_EVENT')
WASTE_EVENT = viz.getEventID('WASTE_EVENT')
POSTER_EVENT = viz.getEventID('POSTER_EVENT')

"""
Events
"""

class EventHandler(viz.EventClass):
    def __init__(self):
        viz.EventClass.__init__(self)
        self.callback(START_EVENT, self.onStart)
        self.callback(DISCARD_EVENT, self.onDiscard)
        self.callback(ORDER_EVENT, self.onOrder)
        self.callback(DELIVER_EVENT, self.onDeliver)
        self.callback(EXPIRE_EVENT, self.onExpiration)
        self.callback(GARBAGE_EVENT, self.onGarbage)
        self.callback(CUSTOMER_ENTER_EVENT, self.onCustomerEnter)
        self.callback(CUSTOMER_LEAVE_EVENT, self.onCustomerLeave)
        self.callback(GRAVITY_EVENT, self.onGravity)
        self.callback(OBJECT_ZEROG_EVENT, self.onObjectZeroG)
        self.callback(SHUFFLE_CARDS_EVENT, self.onShuffleCards)
        self.callback(CLOCK_EVENT, self.onClock)
        self.callback(BIN_EVENT, self.onBin)
        self.callback(STARE_EVENT, self.onStare)
        self.callback(MANNEQUIN_EVENT, self.onMannequin)
        self.callback(WASTE_EVENT, self.onWaste)
        self.callback(POSTER_EVENT, self.onPoster)

    def onStart(self,*args,**kwargs):
        pass

    def onDiscard(self,object,*args,**kwargs):
        if object in dynamicItems:
            dynamicItems.remove(object)
        itemRegistry.pop(object,None)
        object.remove()
            
    def _placeOrderItem(self,item,parent,offset):
        if offset == 0:
            offset = [0,0,0]        
        if parent:
            item.link = viz.link(parent.obj,item.obj)
            item.link.preTrans(offset)
            item.obj.disable(viz.PHYSICS) # Disable Physics to prevent weirdness
        else:
            x,y,z = offset
            u,v,w = spawns['order']
            y += 0.02 # Prevents weird physics results
            item.obj.setPosition([u+x,v+y,w+z])
    
    def onOrder(self,order,*args,**kwargs):
        objects = []
        tray = None
        numCups = 0        
        obj_orderCard.texture(tableCardTextures[order.table_id-1])
        obj_orderCard.visible(1)
        
        if len(order.request) > TRAY_REQUEST_SIZE:
            # Add tray for multiple objects
            tray = obj_tray.copy()
            self._placeOrderItem(tray,None,0)
            objects.append(tray.obj)
        for item in order.request:
            if item == 'cup':
                numCups += 1
                if numCups <= 2: # 2 cups max for now
                    cup = obj_cup.copy()
                    posz = 0.15 - 0.1 * numCups
                    self._placeOrderItem(cup,tray,[.15,.01,posz])                
                    objects.append(cup.obj)
            else:
                # Add plate for food items
                plate = obj_plate.copy()
                self._placeOrderItem(plate,tray,[-.06,.01,0])
                if item == 'pie':
                    food = obj_pie.copy()
                else:
                    food = obj_bread.copy()
                self._placeOrderItem(food,plate,[0,.01,0])
                objects.extend([food.obj,plate.obj])
        order.items = objects
        viz.sendEvent(ASSEMBLE_EVENT, objects)

    def onDeliver(self,order,complete,*args,**kwargs):
        if complete:
            obj_orderCard.visible(0)
            if order.customer.avatar:
                order.customer.avatar.eat()
        for table in tables:
            if table.id == order.table_id:
                table.deliver(order)

    def onExpiration(self,order,*args,**kwargs):
        for obj in order.items:
            if obj not in order.delivered:
                self.onDiscard(obj)
        obj_orderCard.visible(0)

    def _makeDisposable(self,obj,discardFood=True):
        dyno = itemRegistry[obj]
        dyno.disposable = True
        if dyno.category == 'cup':
            obj.getChild('cupCoffee').visible(0)
        elif dyno.category == 'food':
            if not discardFood:
                for name in obj.getNodeNames():
                    if 'main' in name:
                        obj.getChild(name).visible(0)
                    elif 'consumed' in name:
                        obj.getChild(name).visible(1)
            else:
                self.onDiscard(obj)
                return

        elif dyno.category == 'plate':
            obj.texture(tex_dirtyPlate)

        if isinstance(dyno.link,viz.VizLink):
            pos = obj.getPosition(mode=viz.ABS_GLOBAL)
            ori = obj.getEuler(mode=viz.ABS_GLOBAL)
            dyno.link.remove()
            pos[1] += 0.04
            obj.setPosition(pos)
            obj.setEuler(ori)

        obj.enable(viz.PHYSICS)

    def _consume(self,obj,leaveFood=False):
        dyno = itemRegistry[obj]


    def onGarbage(self,order,*args,**kwargs):
        for obj in order.delivered:
            dyno = itemRegistry[obj]
            if not dyno.disposable:
                self._makeDisposable(obj)

    def onCustomerEnter(self,customer,*args,**kwargs):
        if customer.avatar:
            customer.avatar.sit(customer.table_id,customer.seat)

    def onCustomerLeave(self,customer,*args,**kwargs):
        if customer.avatar:
            customer.avatar.leave()

    def onGravity(self,force,*args,**kwargs):
        if force == ZEROG:
            for a in avatars:
                a.avatar.state(ANIM_SIT_WONDER)

    def onObjectZeroG(self,obj,*args,**kwargs):
        self._makeDisposable(obj,discardFood=False)

    def onShuffleCards(self,sequence,*args,**kwargs):
        for n,table in enumerate(tables):
            table.setID(sequence[n])

    def onClock(self,t,*args,**kwargs):
        for clock in clocks:
            clock.setTime(t)
            
    def onBin(self,spawn,*args,**kwargs):
        obj_bin.obj.setPosition(spawn[:3])
        obj_bin.obj.setEuler([spawn[3],0,spawn[4]])

    def onStare(self,state,*args,**kwargs):
        for a in avatars:
            a.stare(state)

    def onMannequin(self,avatar,state,*args,**kwargs):
        for a in avatars:
            a.isMannequin = state # New avatars spawn as mannequins
        if avatar:
            avatar.setMannequin(state)

    def onWaste(self,pos):
        waste = obj_waste.copy()
        waste.disposable = True
        waste.obj.setPosition(pos)
        viz.sendEvent(ASSEMBLE_EVENT, [waste.obj])
    
    def onPoster(self,poster):
        poster.swap()

eventHandler = EventHandler() # Start listening to events


"""
Resources
"""

utils.setRes()

env_cafe = viz.add('dreamcafe.osgb')
env_cafe.collideMesh()
env_cafe.collidePlane()
env_cafe.disable(viz.DYNAMICS)

tex_shadow = viz.addTexture('shadow.png')

# Objects
obj_orderCard = viz.addChild('ordercard.osgb')
ocPos = spawns['order']
obj_orderCard.setPosition([ocPos[0]+0.1,ocPos[1],ocPos[2]+0.3])
obj_orderCard.setEuler([-30,0,0])
obj_orderCard.visible(0)

class PhysicsObject():
    def __init__(self,object,category,collider=0,material='default'):
        if isinstance(object,str):
            object = viz.addChild(object)
        self.obj = object
        self.link = None # Used for parenting
        self.disposable = False # Mark as garbage
        self.category = category # Can be string or list
        self.setCollider(collider)
        self.setMaterial(material)
        itemRegistry[self.obj] = self

    def setCollider(self,shape,replace=False):
        if replace:
            self.collider = self.obj.collideNone()
        if shape == 0:
            self.collider = self.obj.collideBox()
        elif shape == 1:
            self.collider = self.obj.collideSphere()
        elif shape == 3:
            self.collider = self.obj.collideCapsule()
        elif shape == 5:
            self.collider = self.obj.collideMesh()
            self.obj.disable(viz.DYNAMICS)
        else:
            viz.logWarn('**WARNING: Physics shape not available.')
        self.obj.enable(viz.COLLIDE_NOTIFY)

    def setMaterial(self,material):
        self.material = material
        if self.collider and material in materialProperties:
            p = materialProperties[material]
            self.collider.setBounce(p['bounce'])
            self.collider.setDensity(p['density'])
            self.collider.setFriction(p['friction'])
            self.collider.setHardness(p['hardness'])

class DynamicObject(PhysicsObject):
    def __init__(self,object,category,collider=0,material='default'):
        PhysicsObject.__init__(self,object,category,collider=collider,material=material)
        self.obj.visible(0)

    def copy(self):
        new = PhysicsObject(self.obj.copy(),self.category,collider=self.collider.getType(),material=self.material)
        dynamicItems.append(new.obj) #Only append copies, not originals!
        new.obj.visible(1)
        # Hide consumed meshes of food
        if self.category == 'food':
            for name in new.obj.getNodeNames():
                if 'consumed' in name:
                    new.obj.getChild(name).visible(0)
        return new

class TargetObject(PhysicsObject):
    def __init__(self,object,category,collider=0,material='default'):
        PhysicsObject.__init__(self,object,category,collider=collider,material=material)
        self.obj.disable(viz.DYNAMICS)
        targetItems.append(self.obj)

obj_tray = DynamicObject('tray.osgb', 'tray')
obj_plate = DynamicObject('plate.osgb', 'plate')
obj_cup = DynamicObject('coffeecup.osgb', 'cup')
obj_pie = DynamicObject('pie.osgb', 'food')
obj_bread = DynamicObject('bread.osgb', 'food')
obj_waste = DynamicObject('waste.osgb', 'garbage')


tex_dirtyPlate = viz.addTexture('dirty_plate.tga')

obj_trayTarget = TargetObject(env_cafe.getChild('trayStack'), 'tray')
obj_plateTarget = TargetObject(env_cafe.getChild('tubTop'), 'plate')

obj_bin = TargetObject('bin.osgb', ['cup','food','garbage'], collider=3)
eventHandler.onBin(spawns['bin'][0])

# Tables

tables = []
tableCardTextures = []

obj_tableCard = viz.add('tablecard.osgb')
obj_tableCard.visible(0)

seat_offset = [0.21,0.32]           #xz avatar relative to center table
delivery_offset = [0.235,0.32]      #xz object relative to center table
cup_offset = [                      #xz offset to center if multiple cups
    [0.06,-0.16],
    [0.10,-0.08]
    ]

class Table():
    def __init__(self,id,object):
        self.obj = object
        self.bb = object.getBoundingBox()
        self.sensor = None # Use for proximity sensor

        self.seats = []
        self.deliverPoints = []
        self.polarity = [[-1,1],[-1,-1],[1,1],[1,-1]] # polarity for offsetting objects around table
        for p in self.polarity:
            self.seats.append(self._getRelPos(seat_offset,p,False))
            self.deliverPoints.append(self._getRelPos(delivery_offset,p,True))

        # Set card & ID
        self.card = obj_tableCard.copy()
        self.card.setPosition(spawns['card'][str(id)])
        self.card.visible(1)
        self.setID(id)

    def _getRelPos(self,spawn,modifier,onTable):
        x = self.bb.center[0] + spawn[0] * modifier[0]
        y = self.bb.ymax if onTable else 0
        z = 0
        if len(spawn) == 2:
            z = self.bb.center[2] + spawn[1] * modifier[1]
        elif len(spawn) > 2:
            y = self.bb.center[1] + spawn[1]
            z = self.bb.center[2] + spawn[2] * modifier[1]
        return [x,y,z]

    def setID(self,n):
        self.id = n
        self.card.texture(tableCardTextures[n-1])

    def deliver(self,order):
        dpos = self.deliverPoints[order.seat-1][:] # Copy!
        p = self.polarity[order.seat-1]
        rot = -90 if dpos[0] > self.bb.center[0] else 90

        # Count cups
        numCups = 0
        dCups = 0
        for req in order.request:
            if req == 'cup':
                numCups += 1
        for obj in order.delivered:
            dyno = itemRegistry[obj]
            if dyno.category == 'cup':
                dCups += 1

        # Deliver
        for obj in order.delivered:
            dyno = itemRegistry[obj]
            if not dyno.link:
                obj.disable(viz.PHYSICS) ### Prevent stealing food
                if dyno.category == 'cup':
                    cx,cz = cup_offset[numCups - dCups]
                    dpos[0] += cx * -p[0]
                    dpos[2] += cz * -p[0]
                move = vizact.moveTo(dpos,speed=1,mode=viz.ABS_GLOBAL)
                rotate = vizact.spinTo(euler=[rot,0,0],speed=180,mode=viz.ABS_GLOBAL)
                delivery = vizact.parallel(rotate,move)
                obj.addAction(delivery)
                dyno.link = 'hack' #Dirty fix for partial delivery


tableNodes = ['table01','table09','table02','table07']

for i,node in enumerate(tableNodes):
    tableCardTextures.append(viz.addTexture('tableCard{}.tga'.format(i+1)))
    tables.append(Table(i+1,env_cafe.getChild(node)))


# Avatars

MAX_HEADYAW = 80
RET_HEADYAW = 180 - MAX_HEADYAW
MAX_HEADPITCH = 40

ANIM_EAT = 1
ANIM_SIT_IDLE = 2
ANIM_SIT_WONDER = 2 #Use for Zero Gravity

obj_mannequin_f = viz.add('mannequin_f.osgb')
obj_mannequin_f.visible(0)

class Avatar(viz.EventClass):
    def __init__(self,name):
        viz.EventClass.__init__(self)
        self.name = name
        self.avatar = viz.add(name)
        self.avatar.disable(viz.CULL_FACE)
        self.avatar.emissive([0.78]*3) # Lighting fix
        self.avatar.visible(0)

        self.mannequin = obj_mannequin_f.copy()
        self.mannequin.visible(0)
        self.isMannequin = False # Use to spawn as mannequin

        self.transport = viz.addGroup()
        viz.link(self.transport, self.avatar)
        viz.link(self.transport, self.mannequin)

        self.shadow = vizshape.addQuad(parent=self.transport,axis=vizshape.AXIS_Y)
        self.shadow.texture(tex_shadow)
        self.shadow.zoffset()
        self.shadow.alpha(0.5)
        self.shadow.visible(0)

        # Setup lookat, works with VCC.
        self.head = self.avatar.getbone('Bip01 Head')
        self.neck = self.avatar.getbone('Bip01 Neck')
        self.lookatNode = viz.addGroup()
        self.lookatLink = viz.link(self.head,self.lookatNode,mask=viz.LINK_POS)
        self.lookatTarget = None

        self.callback(viz.TIMER_EVENT,self.onUpdate)

    def sit(self,table_id,seat):
        for table in tables:
            if table_id == table.id:
                spos = table.seats[seat-1]
                self.transport.setPosition(spos)
                mpr = -1 if spos[0] > table.bb.center[0] else 1
                self.transport.setEuler([90*mpr,0,0])
                self.avatar.state(ANIM_SIT_IDLE)
        self.setMannequin(self.isMannequin)
        self.shadow.visible(1)

    def eat(self):
        self.avatar.state(ANIM_EAT)

    def leave(self):
        for x in [self.avatar,self.mannequin,self.shadow]:
            x.visible(0)

    def setMannequin(self,state):
        self.avatar.visible(not state)
        self.mannequin.visible(state)

    def stare(self,state,lookat=viz.MainView):
        if state:
            self.lookatTarget = lookat
            self.head.lock()
            self.neck.lock()
            self.starttimer(101,viz.FASTEST_EXPIRATION,viz.FOREVER)
        else:
            if self.lookatTarget:
                self.killtimer(101)
            self.lookatTarget = None
            self.head.unlock()
            self.neck.unlock()

    def onUpdate(self,id):
        if id == 101 and self.lookatTarget:
            self.lookatNode.lookAt(self.lookatTarget.getPosition(),mode=viz.ABS_GLOBAL)
            yaw,pitch,roll = self.lookatNode.getEuler(mode=viz.ABS_GLOBAL)
            yaw -= self.avatar.getEuler()[0]

            # Limit pitch
            if pitch > MAX_HEADPITCH:
                pitch = MAX_HEADPITCH
            elif pitch < - MAX_HEADPITCH:
                pitch = -MAX_HEADPITCH
            pitch += 5 #Lookat Height fix

            #Limit yaw
            if RET_HEADYAW > yaw > MAX_HEADYAW:
                yaw = MAX_HEADYAW
            elif -RET_HEADYAW < yaw < -MAX_HEADYAW:
                yaw = -MAX_HEADYAW
            elif yaw > RET_HEADYAW:
                yaw = -yaw + 180
            elif yaw < -RET_HEADYAW:
                yaw = abs(yaw) - 180
            nyaw = yaw * 0.15

            self.head.setEuler([roll,yaw,pitch],mode=viz.AVATAR_LOCAL)
            self.neck.setEuler([0,nyaw,0],mode=viz.AVATAR_LOCAL)


avatar_names = [
    'business01_f','casual02_f','casual05_f','casual15_f','casual26_f','sportive01_f',
    'business01_m','business05_m','casual03_m','casual14_m','casual16_m','casual20_m'
    ]

avatars = [Avatar(path+'_dc.cfg') for path in avatar_names]


# TV Screen

obj_tv = viz.addTexQuad()
obj_tv.setPosition([3.0,2.40,7.12])
obj_tv.setEuler([0,-5,0])
obj_tv.setScale([1.05,0.6,1])
obj_tv.alpha(0.8)

tex_tvbg0 = viz.addTexture('tv_default.png')
obj_tv.texture(tex_tvbg0)


# Clock

clocks = []

class AnalogueClock():
    def __init__(self,hands,parent,ori):
        self.hands = hands
        self.hands.visible(1)
        self.second = hands.getChild('ClockSecond')
        self.minute = hands.getChild('ClockMinute')
        self.hour = hands.getChild('ClockHour')
        self.link = viz.link(parent,self.hands)
        self.link.preEuler([ori,0,0])
        clocks.append(self)

    def setTime(self,t):
        ''' Time format: [H,M,S] '''
        h,m,s = t
        hRot = h%12 * 30 + m * 0.5
        self.hour.setEuler([0,-hRot,0])
        self.minute.setEuler([0,m*-6,0])
        self.second.setEuler([0,s*-6,0])

class DigitalClock():
    def __init__(self,parent,ori,scale=0.3):
        self.attach = viz.addGroup()
        viz.link(parent,self.attach)
        self.scale = scale
        dx = scale * 1
        self.h = self._lcd(-dx)
        self.m = self._lcd(0)
        self.s = self._lcd(dx)
        clocks.append(self)

    def _lcd(self,offset):
        lcd = viz.addText('88',parent=viz.WORLD)
        lcd.font('digital-7m.ttf')
        lcd.color(viz.WHITE)
        lcd.disable(viz.LIGHTING)
        lcd.alignment(viz.ALIGN_CENTER_CENTER)
        lcd.zoffset(-1)
        lcd.setScale([self.scale]*3)
        viz.link(self.attach,lcd,offset=[offset,0,0])
        return lcd

    def setTime(self,t):
        ''' Time format: [H,M,S] '''
        def setLCD(lcd, i):
            lcd.message('{:02d}'.format(i))
        setLCD(self.h,t[0])
        setLCD(self.m,t[1])
        setLCD(self.s,t[2])

if CLOCK_TYPE == 'analogue':
    obj_clockHands = viz.add('clockhands.osgb')
    obj_clockHands.visible(0)
    att_clock = viz.addGroup()
    att_clock.setPosition([2.055,2.456,6.926])
    clockHandsFront = AnalogueClock(obj_clockHands.copy(),att_clock,0)
    clockHandsBack = AnalogueClock(obj_clockHands.copy(),att_clock,180)
else:
    env_cafe.getChild('clock').visible(0) #Hide analogue clock model

digiclock = DigitalClock(obj_tv,0)


# Posters

posters = []

class Poster():
    def __init__(self, obj, textures):
        self.toggle = viz.cycle(range(len(textures)))
        self.obj = obj
        self.textures = [viz.addTexture(tex) for tex in textures]
        self.swap()
        posters.append(self)
        
    def swap(self):
        self.obj.texture(self.textures[self.toggle.next()])
        
poster_kitchen  = Poster(env_cafe.getChild('poster_kitchen'), ['poster_kitchen.tga','poster_kitchen2.tga','poster_kitchen3.tga'])
poster_tv = Poster(obj_tv,  ['tv_default.png','tv_alt.png'])

# SFX
# NOTE: There's no good way of detecting which subnode of the env dynamic objects would collide with,
# so forget the idea of creating different sounds per interaction, unless based only to the dynamic object.
# NOTE: I'm creating flexible sound emitters because there is a limit of 24 on the mix output.

class AbstractSoundEmitter():
    def __init__(self):
        self.emitter = viz.addGroup()
        self.soundlib = {}

    def addSFX(self,path):
        return self.emitter.playsound(path,viz.SOUND_PRELOAD)

    def play(self,sound,position):
        self.emitter.setPosition(position)
        if sound in self.soundlib:
            self.soundlib[sound].play()

class CollisionSoundEmitter(AbstractSoundEmitter):
    def __init__(self):
        AbstractSoundEmitter.__init__()
        self.soundlib = {
            'default' : self.addSFX('.wav')
            }
