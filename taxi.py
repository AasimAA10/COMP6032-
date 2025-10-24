import math
import numpy
import heapq

# a data container object for the taxi's internal list of fares. This
# tells the taxi what fares are available to what destinations at
# what price, and whether they have been bid upon or allocated. The
# origin is notably missing: that's because the Taxi will keep this
# in a dictionary indexed by fare origin, so we don't need to duplicate that
# here.
class FareInfo:

      def __init__(self, destination, price):

          self.destination = destination
          self.price = price
          # bid is a ternary value: -1 = no, 0 = undecided, 1 = yes indicating whether this
          # taxi has bid for this fare. 
          self.bid = 0
          self.allocated = False


''' A Taxi is an agent that can move about the world it's in and collect fares. All taxis have a
    number that identifies them uniquely to the dispatcher. Taxis have a certain amount of 'idle'
    time they're willing to absorb, but beyond that, they go off duty since it seems to be a waste
    of time to stick around. Eventually, they might come back on duty, but it usually won't be for
    several hours. A Taxi also expects a map of the service area which forms part of its knowledge
    base. Taxis start from some fixed location in the world. Note that they can't just 'appear' there:
    any real Node in the world may have traffic (or other taxis!) there, and if its start node is
    unavailable, the taxi won't enter the world until it is. Taxis collect revenue for fares, and 
    each minute of active time, whether driving, idle, or conducting a fare, likewise costs them £1.
'''           
class Taxi:
      
      # message type constants
      FARE_ADVICE = 1
      FARE_ALLOC = 2
      FARE_PAY = 3
      FARE_CANCEL = 4

      '''constructor. The only required arguments are the world the taxi operates in and the taxi's number.
         optional arguments are:
         idle_loss - how much cost the taxi is prepared to absorb before going off duty. 256 gives about 4
         hours of life given nothing happening. Loss is cumulative, so if a taxi was idle for 120 minutes,
         conducted a fare over 20 minutes for a net gain to it of 40, then went idle for another 120 minutes,
         it would have lost 200, leaving it with only £56 to be able to absorb before going off-duty.
         max_wait - this is a heuristic the taxi can use to decide whether a fare is even worth bidding on.
         It is an estimate of how many minutes, on average, a fare is likely to wait to be collected.
         on_duty_time - this says at what time the taxi comes on duty (default is 0, at the start of the 
         simulation)
         off_duty_time - this gives the number of minutes the taxi will wait before returning to duty if
         it goes off (default is 0, never return)
         service_area - the world can optionally populate the taxi's map at creation time.
         start_point - this gives the location in the network where the taxi will start. It should be an (x,y) tuple.
         default is None which means the world will randomly place the Taxi somewhere on the edge of the service area.
      '''
      def __init__(self, world, taxi_num, idle_loss=256, max_wait=50, on_duty_time=0, off_duty_time=0, service_area=None, start_point=None):

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
          # this contains a Fare (object) that the taxi has picked up. You use the functions pickupFare()
          # and dropOffFare() in a given Node to collect and deliver a fare
          self._passenger = None
          # the map is a dictionary of nodes indexed by (x,y) pair. Each entry is a dictionary of (x,y) nodes that indexes a 
          # direction and distance. such a structure allows rapid lookups of any node from any other.
          self._map = service_area
          if self._map is None:
              self._map = self._world.exportMap()
          # path is a list of nodes to be traversed on the way from one point to another. The list is
          # in order of traversal, and does NOT have to include every node passed through, if these
          # are incidental (i.e. involve no turns or stops or any other remarkable feature)
          self._path = []
          # pick the first available entry point starting from the top left corner if we don't have a
          # preferred choice when coming on duty
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
          # this dict maintains which fares the Dispatcher has broadcast as available. After a certain
          # period of time, fares should be removed  given that the dispatcher doesn't inform the taxis
          # explicitly that their bid has not been successful. The dictionary is indexed by 
          # a tuple of (time, originx, originy) to be unique, and the expiry can be implemented using a heap queue
          # for priority management. You would do this by initialising a self._fareQ object as:
          # self._fareQ = heapq.heapify(self._fares.keys()) (once you have some fares to consider)

          # the dictionary items, meanwhile, contain a FareInfo object with the price, the destination, and whether 
          # or not this taxi has been allocated the fare (and thus should proceed to collect them ASAP from the origin)
          self._availableFares = {}

      # This property allows the dispatcher to query the taxi's location directly. It's like having a GPS transponder
      # in each taxi.
      @property
      def currentLocation(self):
          if self._loc is None:
             return (-1,-1)
          return self._loc.index

      #___________________________________________________________________________________________________________________________
      # methods to populate the taxi's knowledge base

      # get a map if none was provided at the outset
      def importMap(self, newMap):
          # a fresh map can just be inserted
          if self._map is None:
             self._map = newMap
          # but importing a new map where one exists implies adding to the
          # existing one. (Check that this puts in the right values!)
          else:
             for node in newMap.items():
                 neighbours = [(neighbour[1][0],neighbour[0][0],neighbour[0][1]) for neighbour in node[1].items()]
                 self.addMapNode(node[0],neighbours) 
          
      # incrementally add to the map. This can be useful if, e.g. the world itself has a set of
      # nodes incrementally added. It can then call this function on the existing taxis to update
      # their maps.
      def addMapNode(self, coords, neighbours):
          if self._world is None:
             return AttributeError("This Taxi does not exist in any world")
          node = self._world.getNode(coords[0],coords[1])
          if node is None:
             return KeyError("No such node: {0} in this Taxi's service area".format(coords))
          # build up the neighbour dictionary incrementally so we can check for invalid nodes.
          neighbourDict = {}
          for neighbour in neighbours:
              neighbourCoords = (neighbour[1], neighbour[2])
              neighbourNode = self._world.getNode(neighbour[1],neighbour[2])
              if neighbourNode is None:
                 return KeyError("Node {0} expects neighbour {1} which is not in this Taxi's service area".format(coords, neighbour))
              neighbourDict[neighbourCoords] = (neighbour[0],self._world.distance2Node(node, neighbourNode))
          self._map[coords] = neighbourDict

      #---------------------------------------------------------------------------------------------------------------------------
      # automated methods to handle the taxi's interaction with the world. You should not need to change these.

      # comeOnDuty is called whenever the taxi is off duty to bring it into service if desired. Since the relevant
      # behaviour is completely controlled by the _account, _onDutyTime, _offDutyTime and _onDutyPos properties of 
      # the Taxi, you should not need to modify this: all functionality can be achieved in clockTick by changing
      # the desired properties.
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

      # clockTick should handle all the non-driving behaviour, turn selection, stopping, etc. Drive automatically
      # stops once it reaches its next location so that if continuing on is desired, clockTick has to select
      # that action explicitly. This can be done using the turn and continueThrough methods of the node. Taxis
      # can collect fares using pickupFare, drop them off using dropoffFare, bid for fares issued by the Dispatcher
      # using transmitFareBid, and any other internal activity seen as potentially useful. 
      def clockTick(self, world):
          # automatically go off duty if we have absorbed as much loss as we can in a day
          if self._account <= 0 and self._passenger is None:
             print("Taxi {0} is going off-duty".format(self.number))
             self.onDuty = False
             self._offDutyTime = self._world.simTime
          # have we reached our last known destination? Decide what to do now.
          if len(self._path) == 0:
             # obviously, if we have a fare aboard, we expect to have reached their destination,
             # so drop them off.
             if self._passenger is not None:
                if self._loc.dropoffFare(self._passenger, self._direction):
                   self._passenger = None
                # failure to drop off means probably we're not at the destination. But check
                # anyway, and replan if this is the case.
                elif self._passenger.destination != self._loc.index:
                   self._path = self._planPath(self._loc.index, self._passenger.destination)
                   
          # decide what to do about available fares. This can be done whenever, but should be done
          # after we have dropped off fares so that they don't complicate decisions.
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
          else:
             pass
       
          self._account -= 1
    
      # called automatically by the taxi's world to update its position. If the taxi has indicated a
      # turn or that it is going straight through (i.e., it's not stopping here), drive will
      # move the taxi on to the next Node once it gets the green light.
      def drive(self, newPose):
          if newPose[0] is None and newPose[1] == -1:
             self._nextLoc = None
             self._nextDirection = -1
          if self._nextLoc is not None:
             if newPose[0] == self._nextLoc and newPose[1] == self._nextDirection:
                nextPose = (None, -1)
                if self._loc is None:
                   nextPose = newPose[0].occupy(newPose[1],self)
                else: nextPose = self._loc.vacate(self._direction,newPose[1])
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
                raise IndexError("Fell of the edge of the world! Index ({0},{1}) is not in this taxi's map".format(
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

      # recvMsg handles various dispatcher messages. 
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
             for fare in self._availableFares.items():
                 if fare[0][1] == args['origin'][0] and fare[0][2] == args['origin'][1]: 
                    del self._availableFares[fare[0]]
                    return

      #_____________________________________________________________________________________________________________________
      # A* path planner (replaces the original DFS)
      def _planPath(self, origin, destination, **args):
          """
          A* path planner for this codebase.

          Map format assumed:
            self._map[node] -> { neighbor_node: (direction, distance) }

          Returns a list of nodes [origin, ..., destination].
          """

          if origin == destination:
              return [origin]

          if origin not in self._map or destination not in self._map:
              return []

          def heuristic(a, b):
              return math.hypot(a[0] - b[0], a[1] - b[1])

          open_heap = []
          heapq.heappush(open_heap, (0.0, 0.0, origin))

          came_from = {}
          g_score = {origin: 0.0}
          closed = set()

          while open_heap:
              f_curr, g_curr, current = heapq.heappop(open_heap)
              if current in closed:
                  continue
              closed.add(current)

              if current == destination:
                  break

              for nbr, (direction, dist) in self._map.get(current, {}).items():
                  step = float(dist) if dist is not None else 1.0
                  tentative_g = g_curr + step
                  if tentative_g < g_score.get(nbr, float("inf")):
                      came_from[nbr] = current
                      g_score[nbr] = tentative_g
                      f = tentative_g + heuristic(nbr, destination)
                      heapq.heappush(open_heap, (f, tentative_g, nbr))

          if destination not in came_from:
              return []

          path = [destination]
          node = destination
          while node != origin:
              node = came_from[node]
              path.append(node)
          path.reverse()
          return path

      #_____________________________________________________________________________________________________________________
      # More permissive bidding so baseline actually serves customers
      def _bidOnFare(self, time, origin, destination, price):
          """
          Decide whether to bid on a fare.

          Safer than the original (checks reachability/expiry/off-duty),
          but more permissive on price so the baseline moves rides.
          """

          # can't take new work if we're carrying someone or we don't know our position
          if self._passenger is not None or self._loc is None:
              return False

          node_here = self._loc
          node_origin = self._world.getNode(origin[0], origin[1])
          node_dest = self._world.getNode(destination[0], destination[1])

          if node_origin is None or node_dest is None:
              return False

          t_to_origin = self._world.travelTime(node_here, node_origin)
          t_to_dest   = self._world.travelTime(node_origin, node_dest)

          # reject unreachable
          if t_to_origin < 0 or t_to_dest < 0:
              return False

          # fare expiry: must reach origin before they give up
          age = self._world.simTime - time
          remaining_wait = self._maxFareWait - age
          if remaining_wait < 0 or t_to_origin > remaining_wait:
              return False

          # don't go off-duty en route to pickup
          if self._account <= 0 or (self._account - t_to_origin) <= 0:
              return False

          # lenient price floor so we actually serve rides
          min_price = max(3.0, 0.2 * t_to_dest + 0.1 * t_to_origin)
          return price >= min_price
