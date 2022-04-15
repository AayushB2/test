"""
Dream Cafe - Experiment module
Version: 0.1.3
Date: 2017-04-12
Author: Erik van den Berge <e.vandenberge@ru.nl>

*******************************************************************************

The experiment module is an executable module that runs the experiment in real-time. All timer and input related stuff happens here.

"""

import viz, vizact, viztask, vizmat, vizproximity
import random, time
import common
from tools import grabber


"""
Experiment
"""

transporter = viz.addGroup()

# Setup Physics
viz.phys.enable()
viz.phys.setGravity(common.GRAVITY)

headCollider = viz.addGroup()
headCollider.collideSphere(radius=0.15)
viz.link(viz.MainView,headCollider)

# View Mechanics

lookBase = viz.addGroup()
viz.link(viz.MainView,lookBase,mask=viz.LINK_POS)

def inView(object):
    inFov = False
    dfov = 70 #half FOV (horiz, incl. buffer)
    lookBase.lookAt(object.getBoundingBox().center)
    ba = lookBase.getEuler(mode=viz.ABS_GLOBAL)[0]
    va = viz.MainView.getEuler()[0]
    r1 = ba - dfov
    r2 = ba + dfov
    if r1 < -180:
        r3 = 180 - (abs(r1)-180)
        if -180 <  va < r2 or r3 < va < 180:
            inFov = True
    elif r2 > 180:
        r3 = -180 + (r2 - 180)
        if r1 < va < 180 or -180 < va < r3:
            inFov = True
    elif r1 < va < r2:
        inFov = True

    # Extra test for culling (in case of large objects)
    result = inFov or not viz.MainWindow.isCulled(object)
    return result

# Debug

class Debugger():
    def __init__(self):
        self.active = common.DEBUG
    def log(self,*args):
        if self.active:
            mesg = ' '.join([str(arg) for arg in args])
            viz.logNotice(mesg)
debug = Debugger()


"""
Object Interaction
"""

grabbers = []

class HandGrabber(viz.EventClass):
    def __init__(self, tracker, model):
        viz.EventClass.__init__(self)
        
        # Workaround for collider not being offset by transporter if applied directly to model
        self.collider = viz.addGroup()
        self.collideRadius = 0.1
        if model:
            self.collideRadius = self._getBoundRadius(model)
        self.collider.collideSphere(radius=self.collideRadius)
        if not common.HANDPHYSICS:
            self.collider.disable(viz.PHYSICS)
        
        colliderLink = viz.link(transporter,self.collider)
        colliderLink.preMultLinkable(tracker)

        self.vector = [0,0,0]
        self.oldPos = self.collider.getPosition(viz.ABS_GLOBAL)
        self.grabbed = None

        # Set grabber tool
        self.tool = grabber.Grabber(usingPhysics=True,usingSprings=False)
        self.tool.setItems(common.dynamicItems)
        self.tool._highlighter = None
        self.tool.setUpdateFunction(self.onUpdate)
        viz.link(self.collider,self.tool)

        grabbers.append(self)

        self.callback(grabber.GRAB_EVENT, self.onGrab)
        self.callback(grabber.RELEASE_EVENT, self.onRelease)

    def _getBoundRadius(self,item):
        return max(item.getBoundingBox(viz.REL_LOCAL).size) / 2.0

    def _getGrabbable(self,item=None,tolerance=0.02):
        item = item if item else self.tool.getIntersection()
        if item:
            d = vizmat.Distance(item.getPosition(viz.ABS_GLOBAL),self.collider.getPosition(viz.ABS_GLOBAL))
            if d < self._getBoundRadius(item) + self.collideRadius + tolerance:
                return True
        return False

    def onUpdate(self,tool):
        if self.grabbed:
            # Keep track of momentum
            newPos = self.collider.getPosition(viz.ABS_GLOBAL)
            self.vector = [a-b for a,b in zip(newPos,self.oldPos)]
            self.oldPos = newPos

    def grab(self):
        # Test if the grabber is actually touching the object; the standard collision test has a much wider radius.
        if self._getGrabbable():
            self.tool.grab() # send grab event

    def onGrab(self,e):
        if e.grabber == self.tool:
            self.grabbed = e.grabbed
            if common.HANDPHYSICS:
                self.collider.disable(viz.PHYSICS)
        elif e.grabber != self.tool and e.grabbed == self.grabbed:
            # Grabbed object is grabbed by other grabber!
            self.release()

    def release(self,momentum=True):
        if self.grabbed:
            self.momentum = momentum
            self.tool.release()

    def onRelease(self,e):
        if e.grabber == self.tool:
            self.grabbed = None
            if self.momentum:
                e.released.applyForce(dir=self.vector,duration=viz.getFrameElapsed()*2.0) # carry momentum over to released object
                self.momentum = False
            if common.HANDPHYSICS:
                viztask.schedule(self._releasePhysics(e.released))

    def _releasePhysics(self,released):
        # Make sure controller isn't touching the released object anymore before turning on physics again.
        while self._getGrabbable(item=released):
            yield viztask.waitFrame(1)        
            self.collider.enable(viz.PHYSICS)

    def addItems(self,items):
        self.tool.addItems(items)

    def removeItems(self,items):
        self.tool.removeItems(items)


class AbstractController():
    def __init__(self):
        self.controller = None
        self.grabber = None
        viztask.schedule(self._waitInput)

    def _waitInput(self):
        pass

class ViveController(AbstractController):
    def __init__(self,controller):
        AbstractController.__init__(self)
        self.controller = controller
        self.grabber = HandGrabber(controller,controller.model)

    def _waitInput(self):
        while True:
            yield viztask.waitSensorDown(self.controller, steamvr.BUTTON_TRIGGER)
            self.grabber.grab()
            yield viztask.waitSensorUp(self.controller, steamvr.BUTTON_TRIGGER)
            self.grabber.release()

class DebugController(AbstractController):
    def __init__(self,tracker):
        AbstractController.__init__(self)
        hand = viz.addChild('soccerball.osgb')
        handLink = viz.link(tracker,hand)
        handLink.postMultLinkable(viz.MainView)
        self.grabber = HandGrabber(hand,hand)

    def _waitInput(self):
        while True:
            yield viztask.waitMouseDown(viz.MOUSEBUTTON_LEFT)
            self.grabber.grab()
            yield viztask.waitMouseUp(viz.MOUSEBUTTON_LEFT)
            self.grabber.release()


"""
Customers
"""

customers = []
available_avatars = [a for a in common.avatars]
available_seats = []
for table in common.tables:
    for i in range (len(table.seats)):
        available_seats.append([table.id,i+1])

class Customer():
    def __init__(self,avatar,table_id,seat):
        self.avatar = avatar
        self.table_id = table_id
        self.seat = seat

def _placeCustomer(customer):
    if customer.avatar:
        obj = customer.avatar.avatar #placeholder
        for table in common.tables:
            if table.id == customer.table_id:
                obj = table.obj
        while inView(obj):
            yield viztask.waitFrame(common.SLEEP)
    viz.sendEvent(common.CUSTOMER_ENTER_EVENT,customer)
    vizact.ontimer2(common.ORDER_TIME,0,createOrder,customer)
    debug.log('Customer created in seat', customer.table_id, customer.seat)

def createCustomer():
    global customers, available_avatars, available_seats
    debug.log('Creating customer!')
    errormsg = ''
    if not available_seats:
        errormsg += 'seats'
    if not available_avatars:
        if errormsg:
            errormsg += ' or '
        errormsg += 'avatars'

    if errormsg:
        debug.log('Cannot create new customer: No {} available!'.format(errormsg))
    else:
        avatar = random.choice(available_avatars)
        table_id, seat = random.choice(available_seats)
        customer = Customer(avatar,table_id,seat)

        #Administration
        customers.append(customer)
        available_avatars.remove(avatar)
        available_seats.remove([table_id,seat])

        viztask.schedule(_placeCustomer(customer))
        debug.log('Customer Queued for seat', table_id, seat)


"""
Order and Delivery
"""

active_order = None
delivered_orders = []
order_queue = [] # Use  for queuing orders; only one order can be displayed/delivered at a time.

proxyman = vizproximity.Manager()
proxyHeight = 0.2 #height from table

if common.DEBUG:
    proxyman.setDebug(True)

# Create receivers
for table in common.tables:
    proxySize = table.bb.size
    proxySize[1] = proxyHeight
    proxyCenter = table.bb.center
    proxyCenter[1] = table.bb.ymax + proxyHeight / 2.0
    table.sensor = vizproximity.Sensor(vizproximity.Box(proxySize,center=proxyCenter),source=table.obj)
    proxyman.addSensor(table.sensor)

class Order():
    def __init__(self,request,customer):
        self.request = request
        self.customer = customer
        self.table_id = customer.table_id
        self.seat = customer.seat
        self.items = []
        self.delivered = []
        self.cleaned = []
        self.consumed = False

def _queueOrder(order):
    global active_order
    while order_queue[0] != order or viz.phys.getGravity == common.ZEROG:
        yield viztask.waitTime(1)
    active_order = order
    viz.sendEvent(common.ORDER_EVENT, order)
    vizact.ontimer2(common.EXPIRATION_TIME,0, expireOrder, order) # Remove order if undelivered/undeliverable

def createOrder(customer):
    request = []
    numCups = random.choice([0,1,1,2,2,2]) #bias toward multiple cups
    numFood = 1 if numCups == 0 else random.choice([0,1])
    if numCups > 0:
        request.extend(['cup']*numCups)
    if numFood > 0:
        request.append(random.choice(['pie','bread']))
        if numCups > 1 and customer.seat == 4:
            # Tray won't fit in front of seat 4, so never order a tray there (hotfix)
            request.remove('cup')
    order = Order(request,customer)
    order_queue.append(order)
    viztask.schedule(_queueOrder(order))
    debug.log('Order queued for seat', customer.table_id, customer.seat)

# Delivery

def _deliver(order,complete):
    global delivered_orders
    for object in order.delivered:
        try:
            proxyman.remove(object)
        except:
            pass
    for grabber in grabbers:
        if grabber.grabbed in order.delivered:
            grabber.release(momentum=False)
    if not order in delivered_orders:
        delivered_orders.append(order)
    viz.sendEvent(common.DELIVER_EVENT, order, complete)

def deliver(order):
    global active_order
    check = 0
    for i in order.items:
        if i in order.delivered:
            check += 1
    if check == len(order.items):
        active_order = None
        order_queue.remove(order)
        _deliver(order,True)
        setCustomerFinishedTimer(order)
        debug.log('Order delivered for seat', order.table_id, order.seat)
    elif check > 0 and len(order.request) <= common.TRAY_REQUEST_SIZE:
        _deliver(order,False)
        debug.log('Partial Order Delivered for Seat: {} {}!'.format(order.table_id,order.seat))
        
def onEnterProximity(e):
    # Check delivery
    global active_order
    if active_order:
        for table in common.tables:
            if e.sensor == table.sensor and active_order.table_id == table.id and e.target in active_order.items:
                active_order.delivered.append(e.target)
                deliver(active_order)

proxyman.onEnter(None,onEnterProximity)


# Order expiration

def _expire(order):
    # Expire order only when out of view
    global active_order
    while inView(common.obj_orderCard):
        yield viztask.waitFrame(common.SLEEP)
    for object in order.items:
        try:
            proxyman.remove(object)
        except:
            pass
    if active_order:
        active_order = None
    if order in order_queue:
        order_queue.remove(order)
    if order.delivered:
        # If partial delivery, make sure to complete that cycle.
        setCustomerFinishedTimer(order)
    else:
        # Send customer away
        onCustomerFinished(order, reason='expired')
    viz.sendEvent(common.EXPIRE_EVENT,order)
    
def expireOrder(order):
    if order == active_order:
        expire = True
        for object in order.items:
            for grabber in grabbers:
                if object == grabber.grabbed:
                    expire = False
        if expire:
            debug.log('Expiring order...')
            viztask.schedule(_expire(order))
        else:
            # restart timer
            vizact.ontimer2(common.EXPIRATION_TIME/2.0,0,expireOrder,order)

# Customer Finished

def clearSeat(table_id,seat):
    s = [table_id,seat]
    if not s in available_seats:
        available_seats.append(s)
    debug.log('Seat {} {} available!'.format(table_id, seat))

def _killCustomer(order):
    if order.customer.avatar:
        while inView(order.customer.avatar.avatar):
            yield viztask.waitFrame(common.SLEEP)
        if not order.customer.avatar in available_avatars:
            available_avatars.append(order.customer.avatar)
    if order.customer in customers:
        customers.remove(order.customer)
    viz.sendEvent(common.CUSTOMER_LEAVE_EVENT,order.customer)
    # Wait a while before making seat available again
    yield viztask.waitTime(common.CLEARSEAT_TIME)
    clearSeat(order.table_id,order.seat)

def _finishConsumption(order):
    # Turn delivered items into garbage (only when eaten and out of view)
    while inView(order.delivered[0]):
        yield viztask.waitFrame(common.SLEEP)
    viz.sendEvent(common.GARBAGE_EVENT,order)
    vizact.ontimer2(common.CLEANUP_TIME,0,cleanupContingency,order)

    viztask.schedule(_killCustomer(order))

def onCustomerFinished(order,reason='consumed'):
    debug.log('Customer Finished:', reason)
    if reason == 'consumed':
        if order.delivered and not order.consumed:
            order.consumed = True
            viztask.schedule(_finishConsumption(order))
    else:
        viztask.schedule(_killCustomer(order))

def setCustomerFinishedTimer(order):
    min,max = common.CONSUMPTION_TIME
    t = random.random() * float(max-min) + float(min)
    vizact.ontimer2(int(t),0,onCustomerFinished,order)


# Garbage collect

def cleanup(order):
    global delivered_orders
    if order in delivered_orders:
        delivered_orders.remove(order)

def _cleanupObject(object):
    while inView(object):
        yield viztask.waitFrame(common.SLEEP)
    viz.sendEvent(common.DISCARD_EVENT, object)

def cleanupContingency(order):
    # Make sure table/seat get cleared if ExitProximity fails
    for item in order.delivered:
        if not item in order.cleaned:
            viztask.schedule(_cleanupObject(item))
    cleanup(order)

def onExitProximity(e):
    if viz.phys.getGravity != common.ZEROG:
        # Don't trigger in zero gravity
        for order in delivered_orders:
            if order.consumed and e.target in order.delivered and not e.target in order.cleaned:
                order.cleaned.append(e.target)
                debug.log('cleaning order on seat', order.table_id, order.seat)
                if len(order.cleaned) == len(order.delivered):
                    cleanup(order)

proxyman.onExit(None,onExitProximity)

"""
Discard
"""

def attemptDiscard(target,object):
    taro = common.itemRegistry[target]
    dyno = common.itemRegistry[object]
    # Check if disposable and if categories match
    tarCat = taro.category if isinstance(taro.category, list) else [taro.category]
    if dyno.disposable and dyno.category in tarCat:
        object.disable(viz.PHYSICS)
        for grabber in grabbers:
            if object == grabber.grabbed:
                grabber.release()
            grabber.removeItems([object])
        viz.sendEvent(common.DISCARD_EVENT,object)


"""
Table Card Shuffle
"""

current_card_sequence = []
waiting_shuffle = True

def shuffleCards(reset=False):
    global current_card_sequence

    def _updateOrders(order_array):
        for order in order_array:
            order.table_id = seq[current_card_sequence.index(order.table_id)]
    def _updateSeats():
        for seat in available_seats:
            seat[0] = seq[current_card_sequence.index(s[0])]

    if not active_order: # Things will break if shuffled during active order.
        if reset:
            seq = [i+1 for i in range(len(common.tables))]
        else:
            seq = [x for x in current_card_sequence]
            while seq == current_card_sequence:
                random.shuffle(seq)

        # Update Orders and Seats
        if current_card_sequence:
            _updateOrders(order_queue)
            _updateOrders(delivered_orders)
            _updateSeats()

        current_card_sequence = seq
        viz.sendEvent(common.SHUFFLE_CARDS_EVENT,seq)

        if reset:
            debug.log('Cards Reset.')
        else:
            debug.log('Cards Shuffled!')

def cardsInView():
    check = []
    for table in common.tables:
        check.append(inView(table.card))
    print check
    return False if check == [False] * len(common.tables) else True

def scheduleCardShuffle():
    global waiting_shuffle
    waiting_shuffle = True
    debug.log('Attempting Card Shuffle!')
    while cardsInView() or active_order:
        yield viztask.waitFrame(common.SLEEP)
    shuffleCards()
    waiting_shuffle = False

shuffleCards(reset=True) #initialize table cards


"""
Clock
"""

tmodes = ['rt','ff','rw']
timeToggle = viz.cycle(tmodes+[None])

class Clock(viz.EventClass):
    def __init__(self):
        viz.EventClass.__init__(self)
        self.t = [0,0,0]
        self.mode = None

        self.setMode('rt')
        self.callback(viz.TIMER_EVENT,self._onTimer)

    def _onTimer(self,id):
        if id == 0: # RT
            lt = time.localtime()
            self.t = [lt.tm_hour,lt.tm_min,lt.tm_sec]
        elif id == 1: # FF
            h,m,s = self.t
            s += 3
            if s >= 60:
                s = s - 60
                m += 1
            if m >= 60:
                m = m-60
                h += 1
            self.t = [h,m,s]
        elif id == 2: # RW
            h,m,s = self.t
            s -= 1
            if s < 0:
                s = 60 + s
                m -= 1
            if m < 0:
                m = 60 + m
                h -= 1
            self.t = [h,m,s]
        viz.sendEvent(common.CLOCK_EVENT,self.t)

    def setMode(self,mode):
        if self.mode:
            self.killtimer(tmodes.index(self.mode))
        if mode == 'rt' or mode == 'rw':
            self.starttimer(tmodes.index(mode),1,viz.FOREVER)
        elif mode == 'ff':
            self.starttimer(1,viz.FASTEST_EXPIRATION,viz.FOREVER)
        self.mode = mode

mainClock = Clock()


"""
Gravity
"""

gravToggle = viz.cycle([common.ZEROG, common.GRAVITY])

def _zeroG(obj, waitView=False):
    if waitView:
        while inView(obj):
            yield viztask.waitFrame(common.SLEEP)
    if viz.phys.getGravity() == common.ZEROG: #Check if still 0 gravity after wait
        # Boost object to make it float.
        N = (0.4 + 0.6 * random.random()) * 0.001 #force
        p = random.choice([1,-1]) #direction
        force = [p*N,N,p*N]
        viz.sendEvent(common.OBJECT_ZEROG_EVENT,obj)
        obj.applyForce(force,viz.getFrameElapsed()*3)


def setGravity(force):
    global active_order, delivered_orders
    if force == common.ZEROG:
        debug.log('Zero Gravity activated!')
        # Treat active order as delivered to stop delivery system
        if active_order:
            delivered_orders.append(active_order)
            active_order = None
            print 'Active Order is None!'
        for order in delivered_orders:
            order.consumed = True # Customers are too scared to finish eating
            order.cleaned = [x for x in order.delivered] # Mark order as cleaned

        for obj in common.dynamicItems:
            obj.enable(viz.PHYSICS) # Make sure Physics are on for interaction
            viztask.schedule(_zeroG(obj))
    else:
        debug.log('Gravity set to {}.'.format(force))
        for order in delivered_orders:
            # Continue orders if we cancelled an active one
            if order in order_queue:
                order_queue.remove(order)
            # Send away customer
            onCustomerFinished(order,reason='scared')

    viz.phys.setGravity(force)
    viz.sendEvent(common.GRAVITY_EVENT,force)


"""
Bin
"""

binToggle = viz.cycle(common.spawns['bin'])
binNode = viz.addGroup()
binNode.setPosition(common.obj_bin.obj.getPosition())

def _moveBin(pos):
    #call with vizschedule
    binNode.setPosition(pos)
    while inView(common.obj_bin.obj) or inView(binNode):
        yield viztask.waitFrame(common.SLEEP)
    viz.sendEvent(common.BIN_EVENT,pos)
    debug.log('Bin moved!')

def moveBin(pos):
    viztask.schedule(_moveBin(pos))

"""
Avatars
"""

stareToggle = viz.cycle([True,False])

def setAvatarStare(state):
    logmessg = 'Avatar Stare On' if state else 'Avatar Stare Off'
    debug.log(logmessg)
    viz.sendEvent(common.STARE_EVENT,state)

mannequinToggle = viz.cycle([True,False])
mannequin_active = False

def _swapMannequin(customer,state):
    obj = customer.avatar.avatar if state else customer.avatar.mannequin
    while inView(obj):
        yield viztask.waitFrame(common.SLEEP)
    if (state and mannequin_active) or (not state and not mannequin_active):
        debug.log('Swapping {} with mannequin: {}'.format(customer.avatar.name,state))
        viz.sendEvent(common.MANNEQUIN_EVENT,customer.avatar,state)


def setMannequin(state):
    global mannequin_active
    mannequin_active = state
    for customer in customers:
        viztask.schedule(_swapMannequin(customer,state))
    viz.sendEvent(common.MANNEQUIN_EVENT,None,state) #Let common know to spawn avatars as mannequins

    logmessg = 'Avatars replaced with mannequins!' if state else 'Mannequins removed'
    debug.log(logmessg)


"""
Waste
"""

def createWaste():
    cx,cy,cz = common.VIVE_OFFSET
    # spawn waste somewhere in a 4x4 space around Vive center
    x = cx + (random.random()-0.5) * 4
    z = cz + (random.random()-0.5) * 4
    viz.sendEvent(common.WASTE_EVENT,[x,0.2,z])
    

"""
Poster
"""

posterToggle = viz.cycle(common.posters)

def _swapPoster(poster):
    while inView(poster.obj):
        yield viztask.waitFrame(common.SLEEP)
    viz.sendEvent(common.POSTER_EVENT,poster)

def swapPoster(poster):
    viztask.schedule(_swapPoster(poster))

"""
Automation
"""

auto_tasks = []

def autoCustomer():
    while True:
        if not len(order_queue) > common.MAX_WAITING_CUSTOMERS - 1:
            createCustomer()
        else:
            debug.log('Cannot create new customer yet!')
        yield viztask.waitTime(random.randint(common.AUTO_CUST_TIME[0],common.AUTO_CUST_TIME[1]))

def autoWaste():
    while True:
        yield viztask.waitTime(random.randint(common.AUTO_WASTE_TIME[0],common.AUTO_WASTE_TIME[1]))
        createWaste()

def autoEvents():
    autoSkip = False # Use autoSkip to trigger new event right away if previous fails
    prev_event = None

    yield viztask.waitTime(common.AUTO_EVENT_TIME[0]) # First wait

    while True:
        e = random.choice(common.AUTO_EVENTS)
        if len(common.AUTO_EVENTS) > 1:
            # Don't repeat events if we can help it
            while e == prev_event:
                e = random.choice(common.AUTO_EVENTS)

        debug.log('Attempting {} event'.format(e))

        if e == 'gravity':
            if viz.phys.getGravity() != common.ZEROG and delivered_orders:
                # Not much will happen if there are no delivered orders
                setGravity(common.ZEROG)
                # Kill active order
                vizact.ontimer2(35,0,setGravity,common.GRAVITY)
            else:
                autoSkip = True

        elif e == 'shuffle':
            if not waiting_shuffle:
                viztask.schedule(scheduleCardShuffle)
            else:
                autoSkip = True

        elif e == 'time':
            tm = timeToggle.next()
            if tm == 'rt': #Skip realtime
                tm = timeToggle.next()
            mainClock.setMode(tm)
            vizact.ontimer2(50,0,mainClock.setMode,'rt')

        elif e == 'bin':
            if binNode.getPosition() == common.obj_bin.obj.getPosition():
                # If binNode is somewhere else, bin is still waiting to move
                moveBin(binToggle.next())
                moveBin(binToggle.next())
            else:
                autoSkip = True

        elif e == 'stare':
            if customers:
                setAvatarStare(True)
                vizact.ontimer2(30,0,setAvatarStare,False)
            else:
                autoSkip = True

        elif e == 'mannequin':
            if customers:
                setMannequin(True)
                vizact.ontimer2(30,0,setMannequin,False)
            else:
                autoSkip = True
                
        elif e == 'poster':
            swapPoster(posterToggle.next())

        if autoSkip:
            debug.log('{} event skipped.'.format(e))
            yield viztask.waitTime(5)
            autoSkip = False
        else:
            prev_event = e
            debug.log('{} event triggered.'.format(e))
            yield viztask.waitTime(random.randint(common.AUTO_EVENT_TIME[0],common.AUTO_EVENT_TIME[1]))


"""
Events
"""

def onItemsCreated(items,*args,**kwargs):
    for object in items:
        proxyman.addTarget(object)
    for grabber in grabbers:
        grabber.addItems(items)

def onCollideBegin(e):
    if e.obj1 in common.targetItems and e.obj2 in common.dynamicItems:
        tbb = e.obj1.getBoundingBox()
        # Check if dynamic object hit the top (opening) of target, or bottom if target is upside down
        if (e.pos[1] > tbb.ymax - 0.02) or (e.obj1.getEuler()[2] == 180.0 and e.pos[1] < tbb.ymin + 0.02):
            attemptDiscard(e.obj1,e.obj2)

def onKeydown(key):
    global auto_tasks
    if key == common.KEY_START:
        if not auto_tasks: # Start
            ac = viztask.schedule(autoCustomer())
            aw = viztask.schedule(autoWaste())
            ae = viztask.schedule(autoEvents())
            auto_tasks.extend([ac,aw,ae])
            viz.sendEvent(common.START_EVENT)
        else: # End
            for task in auto_tasks:
                task.kill()
            auto_tasks = []

    elif key == common.KEY_GRAVITY:
        setGravity(gravToggle.next())

    elif key == common.KEY_SHUFFLE:
        shuffleCards()

    elif key == common.KEY_CUSTOMER:
        createCustomer()

    elif key == common.KEY_CLOCK:
        mainClock.setMode(timeToggle.next())

    elif key == common.KEY_BINMOVE:
        moveBin(binToggle.next())

    elif key == common.KEY_STARE:
        setAvatarStare(stareToggle.next())

    elif key == common.KEY_MANNEQUIN:
        setMannequin(mannequinToggle.next())

    elif key == common.KEY_CANCEL:
        expireOrder(active_order)

    elif key == common.KEY_WASTE:
        createWaste()
    
    elif key == common.KEY_POSTER:
        swapPoster(posterToggle.next())


"""
Execute
"""

if common.VIVE:
    import steamvr
    from ruviz import river

    viz.go(viz.FULLSCREEN)

    transporter.setPosition(common.VIVE_OFFSET)
    transporter.setEuler(common.VIVE_ORI)

    vive = river.Vive()
    viz.link(transporter, vive.transport)
    for controller in vive.getControllers():
        ViveController(controller)

else:
    import vizcam

    walkNav = vizcam.WalkNavigate(moveScale=1)

    viz.fov(65)
    viz.go()
    viz.window.setSize(1600,900)

    from vizconnect.util import virtual_trackers
    mouseTracker = virtual_trackers.ScrollWheel(followMouse = True)
    mouseTracker.distance = 1.8
    DebugController(mouseTracker)


# Callbacks
viz.callback(common.ASSEMBLE_EVENT, onItemsCreated)
viz.callback(viz.COLLIDE_BEGIN_EVENT, onCollideBegin)
viz.callback(viz.KEYDOWN_EVENT, onKeydown)
