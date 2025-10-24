# dispatcher.py
import math
from collections import defaultdict, deque
from typing import Dict, Tuple, List, Optional

# import Taxi only for constants / typing; avoids circulars at runtime
import taxi


def _xy_from(xy) -> Tuple[int, int]:
    """Convert diverse (node/tuple/list/obj) → (x, y) tuple safely."""
    if xy is None:
        return (-1, -1)
    if isinstance(xy, tuple) and len(xy) == 2:
        return (int(xy[0]), int(xy[1]))
    if isinstance(xy, list) and len(xy) == 2:
        return (int(xy[0]), int(xy[1]))
    # objects with .x/.y
    if hasattr(xy, "x") and hasattr(xy, "y"):
        return (int(getattr(xy, "x")), int(getattr(xy, "y")))
    # objects with .index = (x,y)
    if hasattr(xy, "index"):
        idx = getattr(xy, "index")
        if isinstance(idx, (tuple, list)) and len(idx) == 2:
            return (int(idx[0]), int(idx[1]))
    # fare-like object with .origin
    if hasattr(xy, "origin"):
        return _xy_from(getattr(xy, "origin"))
    return (-1, -1)


def _price_from(fare) -> Optional[float]:
    """Extract price if present on a fare-like object."""
    for nm in ("price", "fare", "amount", "cost"):
        if hasattr(fare, nm):
            try:
                return float(getattr(fare, nm))
            except Exception:
                pass
    return None


def _max_wait_from(fare, default_val: int = 60) -> int:
    """Extract max_wait style attribute if available."""
    for nm in ("max_wait", "maxWait", "wait_limit", "waitLimit"):
        if hasattr(fare, nm):
            try:
                return int(getattr(fare, nm))
            except Exception:
                pass
    return default_val


class Dispatcher:
    """
    Task 2a Dispatcher:
      - ETA (time-to-arrival) + fairness penalty allocation.
      - Revenue tracking (for logger).
      - '_fares' alias for open-fare counting.
      - Backward compatibility shims for bugfix NetWorld:
          * importMap(mapdict)
          * clockTick(world)
          * addTaxi(taxi), removeTaxi(taxi)
          * newFare(world?, origin, destination, calltime[, price][, max_wait])
          * cancelFare(world, fare)
          * receiveBid/recvBid/bid(origin_xy, taxi)
          * notifyFareCancelled(origin_xy)
          * notifyFareCompleted(...) + aliases
    """

    def __init__(self, parent, taxis: List[taxi.Taxi]):
        self._world = parent
        self._taxis: List[taxi.Taxi] = list(taxis)

        # Fare board: key = (call_time, ox, oy, dx, dy)
        # value = {"price": float|None, "max_wait": int, "allocated": taxi_number|None}
        self._fareBoard: Dict[Tuple[int, int, int, int, int], Dict] = {}
        self._fares = self._fareBoard  # alias used by logger/open-fare counters

        # Bids indexed by origin (ox, oy)
        self._bids: Dict[Tuple[int, int], set] = defaultdict(set)

        # Fairness memory (sliding window minutes of recent allocations)
        self._assign_window_minutes = 180
        self._assign_history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=64))

        # Revenue tracker (exposed via getRevenue / .revenue)
        self._revenue: float = 0.0

    # ---------------------------------------------------------------------------------
    # Minimal hooks / compatibility with NetWorld
    # ---------------------------------------------------------------------------------

    def importMap(self, mapdict):
        """NetWorld.addDispatcher calls dispatcher.importMap(exportMap()). Not used here."""
        return None

    def clockTick(self, world):
        """NetWorld.runWorld may call dispatcher.clockTick(world) each tick."""
        return None

    def addTaxi(self, t: taxi.Taxi):
        """Called by NetWorld.addTaxi(...) — must exist."""
        if t not in self._taxis:
            self._taxis.append(t)

    def removeTaxi(self, t: taxi.Taxi):
        if t in self._taxis:
            self._taxis.remove(t)

    # ---------------------------------------------------------------------------------
    # Public API: Fare announcements / bids / cancellations / completions
    # ---------------------------------------------------------------------------------

    def announceFare(self, call_time: int, origin_xy: Tuple[int, int],
                     dest_xy: Tuple[int, int], price: Optional[float], max_wait: int):
        """Modern entry point used by our own code paths."""
        key = (int(call_time), origin_xy[0], origin_xy[1], dest_xy[0], dest_xy[1])
        if key in self._fareBoard:
            return
        self._fareBoard[key] = {
            "price": None if price is None else float(price),
            "max_wait": int(max_wait),
            "allocated": None,
        }
        # Broadcast advice to all taxis
        for t in self._taxis:
            try:
                t.recvMsg(
                    taxi.Taxi.FARE_ADVICE,
                    origin=origin_xy,
                    destination=dest_xy,
                    price=self._fareBoard[key]["price"] if self._fareBoard[key]["price"] is not None else 0.0,
                )
            except Exception:
                pass

    # Aliases commonly used elsewhere
    adviseFare = announceFare
    notifyNewFare = announceFare

    # --------- LEGACY: NetWorld.node -> insertFare -> NetWorld.newFare(...) ----------
    # Observed legacy call: self._dispatcher.newFare(self, fare.origin, fare.destination, fare.calltime[, price][, max_wait])
    def newFare(self, *args, **kwargs):
        """
        Accepts a wide set of signatures:
          newFare(world, origin_xy, dest_xy, call_time)
          newFare(world, origin_xy, dest_xy, call_time, price)
          newFare(world, origin_xy, dest_xy, call_time, price, max_wait)
          newFare(call_time, origin_xy, dest_xy, price, max_wait)  # defensive
          newFare(fare=fare_obj)  # defensive
        """
        # Try keyword-only path first
        if "fare" in kwargs and kwargs["fare"] is not None:
            fare = kwargs["fare"]
            origin = _xy_from(getattr(fare, "origin", None))
            dest = _xy_from(getattr(fare, "destination", None))
            ctime = int(getattr(fare, "calltime", 0))
            price = _price_from(fare)
            maxw = _max_wait_from(fare, default_val=60)
            self.announceFare(ctime, origin, dest, price, maxw)
            return

        # Positional variants
        if len(args) >= 4:
            # If world passed first, skip it
            offset = 1 if len(args) >= 4 and hasattr(args[0], "runWorld") else 0

            try:
                origin = _xy_from(args[offset + 0])
                dest = _xy_from(args[offset + 1])
                ctime = int(args[offset + 2])

                # Optional price and max_wait
                price = None
                maxw = 60
                if len(args) > offset + 3:
                    try:
                        price = float(args[offset + 3])
                    except Exception:
                        price = None
                if len(args) > offset + 4:
                    try:
                        maxw = int(args[offset + 4])
                    except Exception:
                        maxw = 60

                self.announceFare(ctime, origin, dest, price, maxw)
                return
            except Exception:
                pass

        # Keyword fallbacks
        ctime = kwargs.get("call_time", kwargs.get("calltime", kwargs.get("time", 0)))
        origin = _xy_from(kwargs.get("origin"))
        dest = _xy_from(kwargs.get("destination"))
        price = kwargs.get("price", None)
        maxw = kwargs.get("max_wait", kwargs.get("maxWait", 60))
        try:
            self.announceFare(int(ctime), origin, dest, None if price is None else float(price), int(maxw))
        except Exception:
            # last-ditch: ignore malformed calls rather than crash
            pass

    # Backward alias to match some code paths
    def cancelFare(self, *args, **kwargs):
        """
        Legacy removal path used by NetWorld.removeFare(self, fare).
        Expected positional: (world, fare)
        """
        origin_xy = None
        try:
            if len(args) >= 2:
                fare = args[1]
                origin_xy = _xy_from(getattr(fare, "origin", None))
            else:
                origin_xy = _xy_from(kwargs.get("origin"))
        except Exception:
            origin_xy = None

        if origin_xy is not None:
            self.notifyFareCancelled(origin_xy)

    # Called by NetWorld when a taxi emits a bid (world.transmitFareBid(...))
    def receiveBid(self, origin_xy: Tuple[int, int], bidder: taxi.Taxi):
        ox, oy = _xy_from(origin_xy)
        self._bids[(ox, oy)].add(bidder)
        self._allocate_if_ready((ox, oy))

    # Aliases to be extra safe
    recvBid = receiveBid
    bid = receiveBid

    # Called by NetWorld when a fare times out (abandoned)
    def notifyFareCancelled(self, origin_xy: Tuple[int, int]):
        origin_xy = _xy_from(origin_xy)
        # inform taxis so they can clear local lists
        for t in self._taxis:
            try:
                t.recvMsg(taxi.Taxi.FARE_CANCEL, origin=origin_xy)
            except Exception:
                pass
        # purge any entries with this origin
        self._purge_origin(origin_xy)

    # Called by NetWorld when payment is made on drop-off
    def notifyFareCompleted(self, t: taxi.Taxi, origin_xy: Tuple[int, int],
                            dest_xy: Tuple[int, int], amount: float):
        # a small cut for dispatcher accounting (the rest goes straight to taxi via world)
        try:
            add = 0.0 if amount is None else max(0.0, float(amount)) / 9.0
            self._revenue += add
        except Exception:
            pass

        # update fairness memory
        self._mark_alloc(t)

        # inform taxi (keeps taxi accounting in sync)
        try:
            t.recvMsg(taxi.Taxi.FARE_PAY, amount=amount, origin=origin_xy, destination=dest_xy)
        except Exception:
            pass

        # purge posted fare
        self._purge_exact(_xy_from(origin_xy), _xy_from(dest_xy))

    # Extra aliases some bases might use
    fareCompleted = notifyFareCompleted
    payment = notifyFareCompleted
    payFare = notifyFareCompleted

    # ---------------------------------------------------------------------------------
    # Revenue exposure for logger
    # ---------------------------------------------------------------------------------
    def getRevenue(self) -> float:
        return float(self._revenue)

    @property
    def revenue(self) -> float:
        return float(self._revenue)

    # ---------------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------------

    def _purge_origin(self, origin_xy: Tuple[int, int]):
        to_del = [k for k in list(self._fareBoard.keys()) if (k[1], k[2]) == origin_xy]
        for k in to_del:
            del self._fareBoard[k]
        if origin_xy in self._bids:
            del self._bids[origin_xy]

    def _purge_exact(self, origin_xy: Tuple[int, int], dest_xy: Tuple[int, int]):
        to_del = [k for k in list(self._fareBoard.keys())
                  if (k[1], k[2]) == origin_xy and (k[3], k[4]) == dest_xy]
        for k in to_del:
            del self._fareBoard[k]
        if origin_xy in self._bids:
            # clear bids for that origin as well
            del self._bids[origin_xy]

    def _mark_alloc(self, t: taxi.Taxi):
        now = getattr(self._world, "simTime", 0)
        dq = self._assign_history[t.number]
        dq.append(now)

    def _jobs_in_window(self, t: taxi.Taxi) -> int:
        now = getattr(self._world, "simTime", 0)
        cutoff = now - self._assign_window_minutes
        dq = self._assign_history[t.number]
        return sum(1 for ts in dq if ts >= cutoff)

    def _eta_minutes(self, t: taxi.Taxi, origin_xy: Tuple[int, int]) -> float:
        try:
            cur_xy = t.currentLocation
            cur = self._world.getNode(cur_xy[0], cur_xy[1])
            org = self._world.getNode(origin_xy[0], origin_xy[1])
            if cur is None or org is None:
                return float("inf")
            tt = self._world.travelTime(cur, org)
            return float(tt) if tt is not None else float("inf")
        except Exception:
            return float("inf")

    def _fairness_penalty(self, t: taxi.Taxi) -> float:
        jobs = self._jobs_in_window(t)
        penalty = 2.0 * jobs
        # tiny boost for taxis in the red
        bal = None
        for nm in ("_account", "account", "balance", "money"):
            if hasattr(t, nm):
                bal = getattr(t, nm)
                break
        try:
            if bal is not None and float(bal) < 0:
                penalty -= 1.0
        except Exception:
            pass
        return penalty

    def _score(self, t: taxi.Taxi, origin_xy: Tuple[int, int]) -> float:
        eta = self._eta_minutes(t, origin_xy)
        fair = self._fairness_penalty(t)
        if math.isinf(eta):
            return float("inf")
        return eta + fair

    def _allocate_if_ready(self, origin_xy: Tuple[int, int]):
        if origin_xy not in self._bids or len(self._bids[origin_xy]) == 0:
            return

        # find fares with this origin (latest first)
        candidates = [k for k in self._fareBoard.keys() if (k[1], k[2]) == origin_xy]
        if not candidates:
            return

        for fkey in sorted(candidates, key=lambda k: k[0], reverse=True):
            if self._fareBoard[fkey]["allocated"] is not None:
                continue

            bidders = list(self._bids[origin_xy])
            if not bidders:
                break

            scored = [(self._score(t, origin_xy), t) for t in bidders]
            scored = [s for s in scored if not math.isinf(s[0])]
            if not scored:
                break

            scored.sort(key=lambda x: x[0])
            winner = scored[0][1]

            # mark allocation and notify
            self._fareBoard[fkey]["allocated"] = winner.number
            try:
                winner.recvMsg(
                    taxi.Taxi.FARE_ALLOC,
                    origin=(fkey[1], fkey[2]),
                    destination=(fkey[3], fkey[4])
                )
            except Exception:
                # failed to notify: undo allocation
                self._fareBoard[fkey]["allocated"] = None
                continue

            # fairness memory update
            self._mark_alloc(winner)

            # this winner shouldn't win a 2nd fare at the same origin in this cycle
            try:
                self._bids[origin_xy].remove(winner)
            except KeyError:
                pass

            # assign only one posted fare per pass
            break
