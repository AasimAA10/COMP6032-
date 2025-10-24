import pygame
import threading
import time
import math
import sys
import json
import os
from datetime import datetime

# project modules
import networld
import taxi
import dispatcher
from ruparams import *  # worldX, worldY, runTime, numDays, displaySize, junctions, streets, fGenDefault, etc.

# -------------------------------
# Reproducibility (if BASE_SEED present)
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
# Task 2b results directory
# -------------------------------
RESULTS_DIR = "results_task2b"
os.makedirs(RESULTS_DIR, exist_ok=True)

# -------------------------------
# Helpers for safe logging
# -------------------------------
def _get_dispatcher_revenue(disp_obj):
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
    return 0.0

def _count_open_fares(disp_obj):
    for name in ("_fares", "fares", "_fareBoard", "openFares"):
        if hasattr(disp_obj, name):
            try:
                container = getattr(disp_obj, name)
                return len(container) if hasattr(container, "__len__") else int(container)
            except Exception:
                pass
    return 0

def _snapshot_metrics(out_dict, tick, disp, taxis):
    """Append a metrics row into out_dict['metrics'] safely."""
    if out_dict is None:
        return
    if "metrics" not in out_dict:
        out_dict["metrics"] = []
    try:
        disp_rev = _get_dispatcher_revenue(disp)
        open_fares = _count_open_fares(disp)
        taxi_balances = []
        on_duty = 0
        for t in taxis:
            bal = None
            for nm in ("_account", "account", "balance", "money"):
                if hasattr(t, nm):
                    bal = getattr(t, nm)
                    break
            taxi_balances.append(float(bal) if bal is not None else None)
            on_duty += 1 if getattr(t, "onDuty", True) else 0

        out_dict["metrics"].append({
            "tick": int(tick),
            "dispatcherRevenue": float(disp_rev),
            "taxiBalances": taxi_balances,
            "onDuty": int(on_duty),
            "openFares": int(open_fares),
        })
    except Exception as e:
        print(f"[WARN] Snapshot failed at t={tick}: {e}")

# --------------------------------
# Simulation thread
# --------------------------------
def runRoboUber(worldX, worldY, runTime, stop, junctions=None, streets=None,
                interpolate=False, outputValues=None, **args):

    if 'fareProb' not in args:
        args['fareProb'] = 0.001
    if 'fareFile' not in args:
        args['fareFile'] = None

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

    print("Creating taxis")
    # Allow longer wait/idle (Task 2b tuning – safe defaults if not defined in ruparams)
    idle_loss = globals().get("T2B_IDLE_LOSS", 480)
    max_wait = globals().get("T2B_MAX_WAIT", 120)

    taxi0 = taxi.Taxi(world=svcArea, taxi_num=100, service_area=svcMap, start_point=(20, 0),
                      max_wait=max_wait, idle_loss=idle_loss)
    taxi1 = taxi.Taxi(world=svcArea, taxi_num=101, service_area=svcMap, start_point=(49, 15),
                      max_wait=max_wait, idle_loss=idle_loss)
    taxi2 = taxi.Taxi(world=svcArea, taxi_num=102, service_area=svcMap, start_point=(15, 49),
                      max_wait=max_wait, idle_loss=idle_loss)
    taxi3 = taxi.Taxi(world=svcArea, taxi_num=103, service_area=svcMap, start_point=(0, 35),
                      max_wait=max_wait, idle_loss=idle_loss)
    taxis = [taxi0, taxi1, taxi2, taxi3]

    print("Adding a dispatcher")
    dispatcher0 = dispatcher.Dispatcher(parent=svcArea, taxis=taxis)
    svcArea.addDispatcher(dispatcher0)

    print("Bringing taxis on duty")
    for onDutyTaxi in taxis:
        onDutyTaxi.comeOnDuty()

    if outputValues is not None and "metrics" not in outputValues:
        outputValues["metrics"] = []

    threadRunTime = runTime
    threadTime = 0
    print("Starting world")

    # Initial snapshot at t=0 so logs are never empty
    _snapshot_metrics(outputValues, tick=0, disp=dispatcher0, taxis=taxis)

    while threadTime < threadRunTime:
        args['ackStop'].wait()
        if stop.is_set():
            threadRunTime = 0
        else:
            svcArea.runWorld(ticks=1, outputs=outputValues)
            if threadTime != svcArea.simTime:
                threadTime += 1

            # Hourly snapshot (and also at minute 1 to show early activity)
            if threadTime % 60 == 0 or threadTime == 1:
                _snapshot_metrics(outputValues, tick=threadTime, disp=dispatcher0, taxis=taxis)

            # Control simulation speed (smaller is faster)
            time.sleep(1)

    # Ensure a final snapshot at end-of-day
    if outputValues is not None:
        last_tick = outputValues["metrics"][-1]["tick"] if outputValues["metrics"] else -1
        if last_tick < runTime:
            _snapshot_metrics(outputValues, tick=runTime, disp=dispatcher0, taxis=taxis)

# --------------------------------
# Optional fare-type recorder
# --------------------------------
if recordFares:
    fareFile = open('./faretypes.csv', 'a')
    print('"{0}"'.format('FareType'), '"{0}"'.format('originX'), '"{0}"'.format('originY'),
          '"{0}"'.format('destX'), '"{0}"'.format('destY'), '"{0}"'.format('MaxWait'), '"{0}"'.format('MaxCost'),
          sep=',', file=fareFile)
else:
    fareFile = None

# --------------------------------
# Pygame setup
# --------------------------------
userExit = threading.Event()
userConfirmExit = threading.Event()
userConfirmExit.set()

pygame.init()
displaySurface = pygame.display.set_mode(size=displaySize, flags=pygame.RESIZABLE)
aspectRatio = worldX / worldY
if aspectRatio > 4 / 3:
    activeSize = (displaySize[0] - 100, (displaySize[0] - 100) / aspectRatio)
else:
    activeSize = (aspectRatio * (displaySize[1] - 100), displaySize[1] - 100)
displayedBackground = pygame.Surface(activeSize)
displayedBackground.fill(pygame.Color(255, 255, 255))
activeRect = pygame.Rect(round((displaySize[0] - activeSize[0]) / 2),
                         round((displaySize[1] - activeSize[1]) / 2),
                         int(activeSize[0]), int(activeSize[1]))

meshSize = (activeSize[0] / worldX, round(activeSize[1] / worldY))

# mesh of drawing positions
positions = [[pygame.Rect(round(x * meshSize[0]),
                          round(y * meshSize[1]),
                          round(meshSize[0]),
                          round(meshSize[1]))
              for y in range(worldY)]
             for x in range(worldX)]
drawPositions = [[displayedBackground.subsurface(positions[x][y]) for y in range(worldY)] for x in range(worldX)]

# junction subsurfaces
jctRect = pygame.Rect(round(meshSize[0] / 4),
                      round(meshSize[1] / 4),
                      round(meshSize[0] / 2),
                      round(meshSize[1] / 2))
jctSquares = [drawPositions[jct[0]][jct[1]].subsurface(jctRect) for jct in junctionIdxs]

# draw edges
for street in streets:
    pygame.draw.aaline(displayedBackground,
                       pygame.Color(128, 128, 128),
                       (round(street.nodeA[0] * meshSize[0] + meshSize[0] / 2),
                        round(street.nodeA[1] * meshSize[1] + meshSize[1] / 2)),
                       (round(street.nodeB[0] * meshSize[0] + meshSize[0] / 2),
                        round(street.nodeB[1] * meshSize[1] + meshSize[1] / 2)))

# draw junctions
for jct in range(len(junctionIdxs)):
    jctSquares[jct].fill(pygame.Color(192, 192, 192))
    pygame.draw.rect(jctSquares[jct], pygame.Color(128, 128, 128),
                     pygame.Rect(0, 0, round(meshSize[0] / 2), round(meshSize[1] / 2)), 5)

# paint initial frame
displaySurface.blit(displayedBackground, activeRect)
pygame.display.flip()

# colour palette for taxis
taxiColours = {}
taxiPalette = [pygame.Color(0, 0, 0),
               pygame.Color(0, 0, 255),
               pygame.Color(0, 255, 0),
               pygame.Color(255, 0, 0),
               pygame.Color(255, 0, 255),
               pygame.Color(0, 255, 255),
               pygame.Color(255, 255, 0),
               pygame.Color(255, 255, 255)]

taxiRect = pygame.Rect(round(meshSize[0] / 3),
                       round(meshSize[1] / 3),
                       round(meshSize[0] / 3),
                       round(meshSize[1] / 3))

fareRect = pygame.Rect(round(3 * meshSize[0] / 8),
                       round(3 * meshSize[1] / 8),
                       round(meshSize[0] / 4),
                       round(meshSize[1] / 4))

# --------------------------------
# Run for N days
# --------------------------------
for run in range(numDays):

    # shared output buffer with sim thread
    outputValues = {'time': [], 'fares': {}, 'taxis': {}}

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

    curTime = 0
    roboUber.start()

    # Display loop
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
                print(f"curTime: {curTime}, world.time: {outputValues['time'][-1]}")

                # full redraw
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

                # fares and taxis that need to be redrawn
                faresToRedraw = dict([
                    (fare_key, dict([
                        (tstamp, pos)
                        for (tstamp, pos) in fare_times.items()
                        if tstamp > curTime
                    ]))
                    for (fare_key, fare_times) in outputValues['fares'].items()
                    if max(fare_times.keys()) > curTime
                ])

                taxisToRedraw = dict([
                    (taxi_id, dict([
                        (tstamp, pos)
                        for (tstamp, pos) in taxi_times.items()
                        if tstamp > curTime
                    ]))
                    for (taxi_id, taxi_times) in outputValues['taxis'].items()
                    if max(taxi_times.keys()) > curTime
                ])

                # draw taxis
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

                # draw fares
                if len(faresToRedraw) > 0:
                    for fare in faresToRedraw.items():
                        newestFareTime = sorted(list(fare[1].keys()))[-1]
                        pygame.draw.polygon(
                            drawPositions[fare[0][0]][fare[0][1]],
                            pygame.Color(255, 128, 0),
                            [
                                (meshSize[0] / 2, meshSize[1] / 4),
                                (meshSize[0] / 2 - math.cos(math.pi / 6) * meshSize[1] / 4,
                                 meshSize[1] / 2 + math.sin(math.pi / 6) * meshSize[1] / 4),
                                (meshSize[0] / 2 + math.cos(math.pi / 6) * meshSize[1] / 4,
                                 meshSize[1] / 2 + math.sin(math.pi / 6) * meshSize[1] / 4)
                            ]
                        )

                displaySurface.blit(displayedBackground, activeRect)
                pygame.display.flip()

                curTime += 1

    # wait for sim-thread end
    roboUber.join()

    # write day log
    try:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join(RESULTS_DIR, f"task2b_day{run+1}_{stamp}.json")
        payload = {
            "day": run + 1,
            "metrics": outputValues.get("metrics", []),
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"[LOG] Wrote {len(payload['metrics'])} records to {out_path}")
    except Exception as e:
        print(f"[WARN] Failed to write day {run+1} log: {e}")

# done
if fareFile:
    fareFile.close()
pygame.quit()
sys.exit()
