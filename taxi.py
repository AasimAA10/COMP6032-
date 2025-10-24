import math
import numpy
import heapq

# a data container object for the taxi's internal list of fares.
class FareInfo:
      def __init__(self, destination, price):
          self.destination = destination
          self.price = price
          self.bid = 0          # -1 no, 0 undecided, 1 yes
          self.allocated = False

class Taxi:
      # message type constants
      FARE_ADVICE = 1
      FARE_ALLOC = 2
      FARE_PAY = 3
      FARE_CANCEL = 4

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
          self._passenger = None
          self._map = service_area
          if self._map is None:
              self._map = self._world.exportMap()
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

      # knowledge base updates
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

      # automated interactions with the world
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
             print("Taxi {0} is going off-duty".format(self.number))
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
          else:
             pass
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

      # ============================
      # HERE ARE THE MODIFIED PARTS
      # ============================

      # A* path planner (cost = network distance, heuristic = straight-line distance)
      def _planPath(self, origin, destination, **args):
          if origin == destination:
              return [origin]

          # Guardrails
          if origin not in self._map or destination not in self._map:
              return []

          def heuristic(a, b):
              # Euclidean on grid coordinates
              return math.hypot(a[0]-b[0], a[1]-b[1])

          open_set = []
          heapq.heappush(open_set, (0.0, origin))
          came_from = {}            # node -> parent
          g = {origin: 0.0}         # cost to reach node
          f = {origin: heuristic(origin, destination)}

          visited = set()

          while open_set:
              _, current = heapq.heappop(open_set)
              if current in visited:
                  continue
              visited.add(current)

              if current == destination:
                  # reconstruct
                  path = [current]
                  while current in came_from:
                      current = came_from[current]
                      path.append(current)
                  path.reverse()
                  return path

              # neighbors from map: dict of neighbour -> (direction, distance)
              for nb, (dirn, dist) in self._map[current].items():
                  tentative_g = g[current] + (dist if isinstance(dist, (int, float)) else 1.0)
                  if nb not in g or tentative_g < g[nb]:
                      g[nb] = tentative_g
                      f[nb] = tentative_g + heuristic(nb, destination)
                      came_from[nb] = current
                      heapq.heappush(open_set, (f[nb], nb))

          # no route
          return []

      # Profit-based bidding with ETA/expiry checks and a safety margin
      def _bidOnFare(self, time, origin, destination, price):
          SAFETY_MARGIN = 5.0  # minutes of slack against expiry
          MIN_PROFIT     = 2.0 # require at least some positive margin

          # must be available
          if self._passenger is not None:
              return False

          # travel times (in minutes)
          o_node = self._world.getNode(origin[0], origin[1])
          d_node = self._world.getNode(destination[0], destination[1])
          if o_node is None or d_node is None or self._loc is None:
              return False

          time_to_origin = self._world.travelTime(self._loc, o_node)
          time_to_dest   = self._world.travelTime(o_node, d_node)
          if time_to_origin <= 0 or time_to_dest <= 0:
              return False

          # can we get there before fare expires?
          time_since_call = self._world.simTime - time
          remaining_window = self._maxFareWait - time_since_call
          if remaining_window < (time_to_origin + SAFETY_MARGIN):
              return False

          # can we afford to even drive there (account is decremented per minute)
          if self._account <= time_to_origin:
              return False

          # naive profit model: price - driving minutes (origin + trip) - small safety
          estimated_cost = time_to_origin + time_to_dest
          profit = price - estimated_cost
          if profit < MIN_PROFIT:
              return False

          # also avoid bidding if we already have an allocated fare pending
          has_alloc = any(f.allocated for f in self._availableFares.values())
          if has_alloc:
              return False

          return True
