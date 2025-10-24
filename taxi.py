# taxi.py — Task 1b + 2b (A* routing + profit-based bidding), keeping original structure
import math
import heapq

class FareInfo:
    def __init__(self, destination, price):
        self.destination = destination
        self.price = price
        self.bid = 0           # -1 no, 0 undecided, 1 yes
        self.allocated = False

class Taxi:

    FARE_ADVICE = 1
    FARE_ALLOC = 2
    FARE_PAY = 3
    FARE_CANCEL = 4

    SAFETY_MARGIN = 5.0   # profit buffer (Task 2b)

    def __init__(self, world, taxi_num, idle_loss=256, max_wait=90, on_duty_time=0, off_duty_time=0, service_area=None, start_point=None):

        self._world = world
        self.number = taxi_num
        self.onDuty = False
        self._onDutyTime = on_duty_time
        self._offDutyTime = off_duty_time
        self._onDutyPos = start_point
        self._dailyLoss = idle_loss
        self._maxFareWait = max_wait
        self._account = 0
        self._loc = None
        self._direction = -1
        self._nextLoc = None
        self._nextDirection = -1
        self._passenger = None
        self._map = service_area if service_area is not None else self._world.exportMap()
        self._path = []
        if self._onDutyPos is None:
            x = 0
            y = 0
            while (x,y) not in self._map and x < self._world.xSize:
                y += 1
                if y >= self._world.ySize:
                    y = 0
                    x += self._world.xSize - 1
            if x >= self._world.xSize:
                raise ValueError("This taxi's world has a map which is a closed loop: no way in!")
            self._onDutyPos = (x,y)
        self._availableFares = {}

    @property
    def currentLocation(self):
        if self._loc is None:
            return (-1,-1)
        return self._loc.index

    # ---------------- KB management ----------------
    def importMap(self, newMap):
        if self._map is None:
            self._map = newMap
        else:
            for node in newMap.items():
                neighbours = [(neighbour[1][0],neighbour[0][0],neighbour[0][1]) for neighbour in node[1].items()]
                self.addMapNode(node[0],neighbours)

    def addMapNode(self, coords, neighbours):
        if self._world is None:
            return AttributeError("This Taxi does not exist in any world")
        node = self._world.getNode(coords[0],coords[1])
        if node is None:
            return KeyError("No such node: {0} in this Taxi's service area".format(coords))
        neighbourDict = {}
        for neighbour in neighbours:
            neighbourCoords = (neighbour[1], neighbour[2])
            neighbourNode = self._world.getNode(neighbour[1],neighbour[2])
            if neighbourNode is None:
                return KeyError("Node {0} expects neighbour {1} which is not in this Taxi's service area".format(coords, neighbour))
            neighbourDict[neighbourCoords] = (neighbour[0],self._world.distance2Node(node, neighbourNode))
        self._map[coords] = neighbourDict

    # ---------------- world integration ----------------
    def comeOnDuty(self, time=0):
        if self._world is None:
            return AttributeError("This Taxi does not exist in any world")
        if self._offDutyTime == 0 or (time >= self._onDutyTime and time < self._offDutyTime):
            if self._account <= 0:
                self._account = self._dailyLoss
            self.onDuty = True
            onDutyPose = self._world.addTaxi(self,self._onDutyPos)
            self._nextLoc = onDutyPose[0]
            self._nextDirection = onDutyPose[1]

    def clockTick(self, world):
        if self._account <= 0 and self._passenger is None:
            # go off duty
            self.onDuty = False
            self._offDutyTime = self._world.simTime
        if len(self._path) == 0:
            if self._passenger is not None:
                if self._loc.dropoffFare(self._passenger, self._direction):
                    self._passenger = None
                elif self._passenger.destination != self._loc.index:
                    self._path = self._planPath(self._loc.index, self._passenger.destination)
        faresToRemove = []
        for fare in self._availableFares.items():
            origin = (fare[0][1], fare[0][2])
            if len(self._path) == 0 and fare[1].allocated and self._passenger is None:
                if self._loc.index[0] == origin[0] and self._loc.index[1] == origin[1]:
                    self._passenger = self._loc.pickupFare(self._direction)
                    if self._passenger is not None:
                        self._path = self._planPath(self._loc.index, self._passenger.destination)
                    faresToRemove.append(fare[0])
                else:
                    self._path = self._planPath(self._loc.index, origin)
            elif self._world.simTime-fare[0][0] > self._maxFareWait:
                faresToRemove.append(fare[0])
            elif fare[1].bid == 0:
                if self._bidOnFare(fare[0][0],origin,fare[1].destination,fare[1].price):
                    self._world.transmitFareBid(origin, self)
                    fare[1].bid = 1
                else:
                    fare[1].bid = -1
        for expired in faresToRemove:
            del self._availableFares[expired]
        self._account -= 1

    def drive(self, newPose):
        if newPose[0] is None and newPose[1] == -1:
            self._nextLoc = None
            self._nextDirection = -1
        if self._nextLoc is not None:
            if newPose[0] == self._nextLoc and newPose[1] == self._nextDirection:
                nextPose = (None, -1)
                if self._loc is None:
                    nextPose = newPose[0].occupy(newPose[1],self)
                else:
                    nextPose = self._loc.vacate(self._direction,newPose[1])
                if nextPose[0] == newPose[0] and nextPose[1] == newPose[1]:
                    self._loc = self._nextLoc
                    self._direction = self._nextDirection
                    if len(self._path) > 0:
                        if self._path[0][0] == self._loc.index[0] and self._path[0][1] == self._loc.index[1]:
                            self._path.pop(0)
                        else:
                            nextPose = self._loc.continueThrough(self._direction)
                            self._nextLoc = nextPose[0]
                            self._nextDirection = nextPose[1]
                            return
                self._nextLoc = None
                self._nextDirection = -1
        if self._nextLoc is None and len(self._path) > 0:
            if self._loc.index not in self._map:
                raise IndexError("Fell off the edge of the world! Index ({0},{1}) is not in this taxi's map".format(
                      self._loc.index[0], self._loc.index[1]))
            if self._path[0][0] == self._loc.index[0] and self._path[0][1] == self._loc.index[1]:
                self._path.pop(0)
                if len(self._path) == 0:
                    return
            if self._path[0] not in self._map[self._loc.index]:
                raise IndexError("Can't get there from here! Map doesn't have a path to ({0},{1}) from ({2},{3})".format(
                                 self._path[0][0], self._path[0][1], self._loc.index[0], self._loc.index[1]))
            nextPose = self._loc.turn(self._direction,self._map[self._loc.index][self._path[0]][0])
            self._nextLoc = nextPose[0]
            self._nextDirection = nextPose[1]

    def recvMsg(self, msg, **args):
        timeOfMsg = self._world.simTime
        if msg == self.FARE_ADVICE:
            callTime = self._world.simTime
            self._availableFares[callTime,args['origin'][0],args['origin'][1]] = FareInfo(args['destination'],args['price'])
            return
        elif msg == self.FARE_ALLOC:
            for fare in self._availableFares.items():
                if fare[0][1] == args['origin'][0] and fare[0][2] == args['origin'][1]:
                    if fare[1].destination[0] == args['destination'][0] and fare[1].destination[1] == args['destination'][1]:
                        fare[1].allocated = True
                        return
        elif msg == self.FARE_PAY:
            self._account += args['amount']
            return
        elif msg == self.FARE_CANCEL:
            for fare in list(self._availableFares.items()):
                if fare[0][1] == args['origin'][0] and fare[0][2] == args['origin'][1]:
                    del self._availableFares[fare[0]]
                    return

    # ---------------- TASK: routing (A*) ----------------
    def _planPath(self, origin, destination, **args):
        """A* over the taxi's _map (which stores neighbour: (dir, distance))."""
        if origin == destination:
            return []

        def heuristic(a, b):
            return abs(a[0]-b[0]) + abs(a[1]-b[1])  # Manhattan is fine

        open_heap = []
        heapq.heappush(open_heap, (0.0, origin))
        came_from = {}
        g = {origin: 0.0}

        while open_heap:
            _, current = heapq.heappop(open_heap)
            if current == destination:
                # reconstruct
                path = []
                node = destination
                while node in came_from:
                    path.append(node)
                    node = came_from[node]
                path.reverse()
                return path

            if current not in self._map:
                continue
            for nbr, (turn_dir, dist) in self._map[current].items():
                tentative = g[current] + float(dist)
                if nbr not in g or tentative < g[nbr]:
                    g[nbr] = tentative
                    f = tentative + heuristic(nbr, destination)
                    heapq.heappush(open_heap, (f, nbr))
                    came_from[nbr] = current
        return []

    # ---------------- TASK: bidding (profit-based) ----------------
    def _bidOnFare(self, time, origin, destination, price):
        NoCurrentPassengers = self._passenger is None
        NoAllocatedFares = len([fare for fare in self._availableFares.values() if fare.allocated]) == 0

        try:
            start = self._loc if self._loc is not None else self._world.getNode(self._onDutyPos[0], self._onDutyPos[1])
            org = self._world.getNode(origin[0], origin[1])
            dest = self._world.getNode(destination[0], destination[1])
            TimeToOrigin = self._world.travelTime(start, org)
            TimeToDestination = self._world.travelTime(org, dest)
        except Exception:
            return False

        if TimeToOrigin is None or TimeToDestination is None:
            return False

        # Profit heuristic: fare price must exceed cost + margin
        # cost model: 0.1 per minute (adjustable) -> divide by 10
        total_minutes = TimeToOrigin + TimeToDestination
        est_cost = total_minutes / 10.0
        profit = float(price) - est_cost - self.SAFETY_MARGIN

        FareExpiryInFuture = self._maxFareWait > self._world.simTime - time
        EnoughTimeToReachFare = self._maxFareWait - (self._world.simTime - time) > TimeToOrigin
        feasible = FareExpiryInFuture and EnoughTimeToReachFare

        NotCurrentlyBooked = NoCurrentPassengers and NoAllocatedFares

        return (profit > 0.0) and feasible and NotCurrentlyBooked
