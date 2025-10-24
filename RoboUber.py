import pygame
import threading
import time
import math
import sys
import json
import copy
import os
from datetime import datetime

# the 3 Python modules containing the RoboUber objects
import networld
import taxi
import dispatcher

# the main parameters are in an editable file
from ruparams import *  # brings in worldX, worldY, runTime, numDays, displaySize, trafficOn, recordFares, junctions/streets, BASE_SEED, etc.

# -------------------------------
# Reproducibility (deterministic)
# -------------------------------
try:
    import random
    import numpy as np
    if "BASE_SEED" in globals():
        random.seed(BASE_SEED)
        np.random.seed(BASE_SEED)
except Exception:
    pass

# -------------------------------
# Results folder for Task 2 logs
# -------------------------------
RESULTS_DIR = "results_task2"
os.makedirs(RESULTS_DIR, exist_ok=True)

def _get_dispatcher_revenue(disp_obj):
    """Try several common attribute/method names to obtain dispatcher revenue."""
    if hasattr(disp_obj, "getRevenue") and callable(disp_obj.getRevenue):
        try:
            return float(disp_obj.getRevenue())
        except Exception:
            pass
    for name in ("revenue", "_revenue", "totalRevenue", "dispatcherRevenue"):
        if hasattr(disp_obj, name):
            try:
                return float(getattr(disp_obj, name))
            except Exception:
                pass
    return None

def _count_open_fares(disp_obj):
    """Try to count currently open/unallocated fares from dispatcher containers."""
    for name in ("_fares", "fares", "_fareBoard", "openFares"):
        if hasattr(disp_obj, name):
            try:
                container = getattr(disp_obj, name)
                return len(container) if hasattr(container, "__len__") else int(container)
            except Exception:
                pass
    return 0

def runRoboUber(worldX, worldY, runTime, stop, junctions=None, streets=None,
                interpolate=False, outputValues=None, **args):
    """
    Runs the world simulation in a background thread.
    Pushes hourly snapshots into outputValues["metrics"] for analysis.
    """

    # initialise a random fare generator
    if 'fareProb' not in args:
        args['fareProb'] = 0.001

    # might have a file for recording fare types (to gather data for learning them)
    if 'fareFile' not in args:
        args['fareFile'] = None

    # create the NetWorld - the service area
    print("Creating world...")
    svcArea = networld.NetWorld(
        x=worldX, y=worldY, runtime=runTime,
        fareprob=args['fareProb'],
        jctNodes=junctions, edges=streets,
        interpolateNodes=interpolate,
        farefile=args['fareFile']
    )
    print("Exporting map...")
    svcMap = svcArea.exportMap()
    if 'serviceMap' in args:
        args['serviceMap'] = svcMap

    # create some taxis (Task 2a: longer on-duty via higher idle_loss and longer max_wait)
    print("Creating taxis")
    taxi0 = taxi.Taxi(world=svcArea, taxi_num=100, service_area=svcMap, start_point=(20, 0),
                      idle_loss=400, max_wait=90)
    taxi1 = taxi.Taxi(world=svcArea, taxi_num=101, service_area=svcMap, start_point=(49, 15),
                      idle_loss=400, max_wait=90)
    taxi2 = taxi.Taxi(world=svcArea, taxi_num=102, service_area=svcMap, start_point=(15, 49),
                      idle_loss=400, max_wait=90)
    taxi3 = taxi.Taxi(world=svcArea, taxi_num=103, service_area=svcMap, start_point=(0, 35),
                      idle_loss=400, max_wait=90)
    taxis = [taxi0, taxi1, taxi2, taxi3]

    # and a dispatcher
    print("Adding a dispatcher")
    dispatcher0 = dispatcher.Dispatcher(parent=svcArea, taxis=taxis)

    # who should be on duty
    svcArea.addDispatcher(dispatcher0)

    # bring the taxis on duty
    print("Bringing taxis on duty")
    for onDutyTaxi in taxis:
        onDutyTaxi.comeOnDuty()

    # ensure 'metrics' list exists in shared output dict
    if outputValues is not None and "metrics" not in outputValues:
        outputValues["metrics"] = []

    threadRunTime = runTime
    threadTime = 0
    print("Starting world")

    while threadTime < threadRunTime:

        # if the program may be quitting, stop execution awaiting user decision
        args['ackStop'].wait()

        # exit if 'q' has been pressed
        if stop.is_set():
            threadRunTime = 0
        else:
            # advance the world by one simulated minute
            svcArea.runWorld(ticks=1, outputs=outputValues)
            if threadTime != svcArea.simTime:
                threadTime += 1

            # Hourly snapshot (change 60->1 for per-minute)
            if outputValues is not None and (threadTime % 60 == 0):
                try:
                    disp_rev = _get_dispatcher_revenue(dispatcher0)
                    open_fares = _count_open_fares(dispatcher0)

                    taxi_balances = []
                    on_duty = 0
                    for t in taxis:
                        bal = None
                        for nm in ("account", "balance", "money", "_account"):
                            if hasattr(t, nm):
                                bal = getattr(t, nm)
                                break
                        taxi_balances.append(float(bal) if bal is not None else None)
                        on_duty += 1 if getattr(t, "onDuty", True) else 0

                    outputValues["metrics"].append({
                        "tick": int(threadTime),
                        "dispatcherRevenue": disp_rev,
                        "taxiBalances": taxi_balances,
                        "onDuty": int(on_duty),
                        "openFares": int(open_fares)
                    })
                except Exception as e:
                    print(f"[WARN] Logging snapshot failed at t={threadTime}: {e}")

            # speed of the simulation (smaller = faster)
            time.sleep(1)


# file to record appearing Fares.
if recordFares:
    fareFile = open('./faretypes.csv', 'a')
    print('"{0}"'.format('FareType'), '"{0}"'.format('originX'), '"{0}"'.format('originY'),
          '"{0}"'.format('destX'), '"{0}"'.format('destY'), '"{0}"'.format('MaxWait'), '"{0}"'.format('MaxCost'),
          sep=',', file=fareFile)
else:
    fareFile = None

# events to manage a user exit
userExit = threading.Event()
userConfirmExit = threading.Event()
userConfirmExit.set()  # enable the simulation thread

# pygame initialisation. Only do this once for static elements.
pygame.init()
displaySurface = pygame.display.set_mode(size=displaySize, flags=pygame.RESIZABLE)
backgroundRect = None
aspectRatio = worldX / worldY
if aspectRatio > 4 / 3:
    activeSize = (displaySize[0] - 100, (displaySize[0] - 100) / aspectRatio)
else:
    activeSize = (aspectRatio * (displaySize[1] - 100), displaySize[1] - 100)
displayedBackground = pygame.Surface(activeSize)
displayedBackground.fill(pygame.Color(255, 255, 255))
activeRect = pygame.Rect(round((displaySize[0] - activeSize[0]) / 2),
                         round((displaySize[1] - activeSize[1]) / 2),
                         activeSize[0], activeSize[1])

meshSize = ((activeSize[0] / worldX), round(activeSize[1] / worldY))

# create a mesh of possible drawing positions
positions = [[pygame.Rect(round(x * meshSize[0]),
                          round(y * meshSize[1]),
                          round(meshSize[0]),
                          round(meshSize[1]))
              for y in range(worldY)]
             for x in range(worldX)]
drawPositions = [[displayedBackground.subsurface(positions[x][y]) for y in range(worldY)] for x in range(worldX)]

# junctions exist only at labelled locations; it's convenient to create subsurfaces for them
jctRect = pygame.Rect(round(meshSize[0] / 4),
                      round(meshSize[1] / 4),
                      round(meshSize[0] / 2),
                      round(meshSize[1] / 2))
jctSquares = [drawPositions[jct[0]][jct[1]].subsurface(jctRect) for jct in junctionIdxs]

# initialise the network edge drawings (as grey lines)
for street in streets:
    pygame.draw.aaline(displayedBackground,
                       pygame.Color(128, 128, 128),
                       (round(street.nodeA[0] * meshSize[0] + meshSize[0] / 2),
                        round(street.nodeA[1] * meshSize[1] + meshSize[1] / 2)),
                       (round(street.nodeB[0] * meshSize[0] + meshSize[0] / 2),
                        round(street.nodeB[1] * meshSize[1] + meshSize[1] / 2)))

# initialise the junction drawings (as grey boxes)
for jct in range(len(junctionIdxs)):
    jctSquares[jct].fill(pygame.Color(192, 192, 192))
    pygame.draw.rect(jctSquares[jct], pygame.Color(128, 128, 128),
                     pygame.Rect(0, 0, round(meshSize[0] / 2), round(meshSize[1] / 2)), 5)

# redraw the entire image
displaySurface.blit(displayedBackground, activeRect)
pygame.display.flip()

# which taxi is associated with which colour
taxiColours = {}
taxiPalette = [pygame.Color(0, 0, 0),
               pygame.Color(0, 0, 255),
               pygame.Color(0, 255, 0),
               pygame.Color(255, 0, 0),
               pygame.Color(255, 0, 255),
               pygame.Color(0, 255, 255),
               pygame.Color(255, 255, 0),
               pygame.Color(255, 255, 255)]

# relative positions of taxi and fare markers in a mesh point
taxiRect = pygame.Rect(round(meshSize[0] / 3),
                       round(meshSize[1] / 3),
                       round(meshSize[0] / 3),
                       round(meshSize[1] / 3))

fareRect = pygame.Rect(round(3 * meshSize[0] / 8),
                       round(3 * meshSize[1] / 8),
                       round(meshSize[0] / 4),
                       round(meshSize[1] / 4))

# you can run for more than a day if desired.
for run in range(numDays):

    # create a dict of things we want to record (shared with the sim thread)
    outputValues = {'time': [], 'fares': {}, 'taxis': {}}
    # metrics snapshots are appended in runRoboUber()

    # create the thread that runs the simulation
    roboUber = threading.Thread(target=runRoboUber,
                                name='RoboUberThread',
                                kwargs={'worldX': worldX,
                                        'worldY': worldY,
                                        'runTime': runTime,
                                        'stop': userExit,
                                        'ackStop': userConfirmExit,
                                        'junctions': junctions,
                                        'streets': streets,
                                        'interpolate': True,
                                        'outputValues': outputValues,
                                        'fareProb': fGenDefault,
                                        'fareFile': fareFile})

    # curTime is the time point currently displayed
    curTime = 0

    # start the simulation (which will automatically stop at the end of the run time)
    roboUber.start()

    # this is the display loop which updates the on-screen output.
    while curTime < runTime:

        try:
            quitevent = next(evt for evt in pygame.event.get() if evt.type == pygame.KEYDOWN)
            if quitevent.key == pygame.K_q:
                userConfirmExit.clear()
                print("Really quit? Press Y to quit, any other key to ignore and keep running")
                while not userConfirmExit.is_set():
                    try:
                        quitevent = next(evt for evt in pygame.event.get() if evt.type == pygame.KEYDOWN)
                        if quitevent.key == pygame.K_y:
                            userExit.set()
                            userConfirmExit.set()
                            roboUber.join()
                            if fareFile:
                                fareFile.close()
                            pygame.quit()
                            sys.exit()
                        userConfirmExit.set()
                    except StopIteration:
                        continue
        except StopIteration:
            if 'time' in outputValues and len(outputValues['time']) > 0 and curTime != outputValues['time'][-1]:
                print("curTime: {0}, world.time: {1}".format(curTime, outputValues['time'][-1]))

                # redraw map
                displayedBackground.fill(pygame.Color(255, 255, 255))

                for street in streets:
                    pygame.draw.aaline(displayedBackground,
                                       pygame.Color(128, 128, 128),
                                       (round(street.nodeA[0] * meshSize[0] + meshSize[0] / 2),
                                        round(street.nodeA[1] * meshSize[1] + meshSize[1] / 2)),
                                       (round(street.nodeB[0] * meshSize[0] + meshSize[0] / 2),
                                        round(street.nodeB[1] * meshSize[1] + meshSize[1] / 2)))

                for jct in range(len(junctionIdxs)):
                    jctSquares[jct].fill(pygame.Color(192, 192, 192))
                    pygame.draw.rect(jctSquares[jct], pygame.Color(128, 128, 128),
                                     pygame.Rect(0, 0, round(meshSize[0] / 2), round(meshSize[1] / 2)), 5)

                # get fares and taxis that need to be redrawn.
                faresToRedraw = dict([(fare[0], dict([(timep[0], timep[1])
                                                      for timep in fare[1].items()
                                                      if timep[0] > curTime]))
                                      for fare in outputValues['fares'].items()
                                      if max(fare[1].keys()) > curTime])

                taxisToRedraw = dict([(taxi_it[0], dict([(taxiPos[0], taxiPos[1])
                                                         for taxiPos in taxi_it[1].items()
                                                         if taxiPos[0] > curTime]))
                                      for taxi_it in outputValues['taxis'].items()
                                      if max(taxi_it[1].keys()) > curTime])

                if len(taxisToRedraw) > 0:
                    for taxi_it in taxisToRedraw.items():
                        if taxi_it[0] not in taxiColours and len(taxiPalette) > 0:
                            taxiColours[taxi_it[0]] = taxiPalette.pop(0)
                        if taxi_it[0] in taxiColours:
                            newestTime = sorted(list(taxi_it[1].keys()))[-1]
                            pygame.draw.circle(
                                drawPositions[taxi_it[1][newestTime][0]][taxi_it[1][newestTime][1]],
                                taxiColours[taxi_it[0]],
                                (round(meshSize[0] / 2), round(meshSize[1] / 2)),
                                round(meshSize[0] / 3)
                            )

                if len(faresToRedraw) > 0:
                    for fare in faresToRedraw.items():
                        _ = sorted(list(fare[1].keys()))[-1]
                        pygame.draw.polygon(
                            drawPositions[fare[0][0]][fare[0][1]],
                            pygame.Color(255, 128, 0),
                            [(meshSize[0] / 2, meshSize[1] / 4),
                             (meshSize[0] / 2 - math.cos(math.pi / 6) * meshSize[1] / 4,
                              meshSize[1] / 2 + math.sin(math.pi / 6) * meshSize[1] / 4),
                             (meshSize[0] / 2 + math.cos(math.pi / 6) * meshSize[1] / 4,
                              meshSize[1] / 2 + math.sin(math.pi / 6) * meshSize[1] / 4)]
                        )

                # redraw
                displaySurface.blit(displayedBackground, activeRect)
                pygame.display.flip()

                # advance time
                curTime += 1

    # wait 'til the simulation thread ends
    roboUber.join()

    # ------------ Write Day Log ------------
    try:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(RESULTS_DIR, f"task2_day{run+1}_{stamp}.json")
        payload = {
            "day": run + 1,
            "metrics": outputValues.get("metrics", []),
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"[LOG] Wrote {len(payload['metrics'])} records to {out_path}")
    except Exception as e:
        print(f"[WARN] Failed to write day {run+1} log: {e}")

# reached the end of the loop. Next day (or exit)
if fareFile:
    fareFile.close()
pygame.quit()
sys.exit()
