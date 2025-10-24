# ruparams.py — parameters & map for RoboUber (Week 5 build)
# This file centralises all tunables and defines the network.

import numpy

# ------------------------
# Deterministic base seed
# ------------------------
BASE_SEED = 42

# ------------------------
# World / run parameters
# ------------------------
worldX = 50
worldY = 50
runTime = 1440          # one day = 1440 ticks
numDays = 1             # multi-day works with bugfix base; keep 1 for week5 tasks
displaySize = (1024, 768)
trafficOn = False
recordFares = False     # set True to append to faretypes.csv

# Fare probabilities (used as magnitudes by fare generator)
fareProbMagnet = 0.02
fareProbPopular = 0.008
fareProbSemiPopular = 0.005
fareProbNormal = 0.001

# traffic toggles
trafficSrcMinor = 1 if trafficOn else 0
trafficSrcSignificant = 2 if trafficOn else 0
trafficSrcMajor = 3 if trafficOn else 0
trafficSrcHub = 4 if trafficOn else 0
trafficSinkMinor = 1 if trafficOn else 0
trafficSinkSignificant = 2 if trafficOn else 0
trafficSinkMajor = 3 if trafficOn else 0
trafficSinkDrain = 4 if trafficOn else 0

# ------------------------
# Fare type initialisers
# ------------------------
fTypeArgs1 = {'normal': {'type_prob': 0.5,
                        'destparams': {'d0': (numpy.array([24, 24]), numpy.array([[6, 0], [0,6]])),
                                       'd1': (numpy.array([15, 40]), numpy.array([[10, 0], [0, 10]])),
                                       'd2': (numpy.array([40, 15]), numpy.array([[10, 0], [0, 10]]))},
                        'waitparams': {'mu': 30, 'sigma': 10},
                        'costparams': {'a': 2, 'b': 4}}}
fTypeArgs1.update({'rich': {'type_prob': 0.05,
                           'destparams': {'d0': (numpy.array([24, 24]), numpy.array([[6, 0], [0,6]]), 1.0),
                                          'd1': (numpy.array([15, 40]), numpy.array([[10, 0], [0, 10]]), 1.0),
                                          'd2': (numpy.array([40, 15]), numpy.array([[10, 0], [0, 10]]), 1.0)},
                           'waitparams': {'min': 15, 'max': 60},
                           'costparams': {'a': 2, 'b': 4, 'scale': 20}}})
fTypeArgs1.update({'hurry': {'type_prob': 0.15,
                            'destparams': {'mu': 10, 'sigma': 5},
                            'waitparams': {'tau': 20},
                            'costparams': {'ceiling': 50}}})
fTypeArgs1.update({'budget': {'type_prob': 0.25,
                             'destparams': {'mu': 10, 'sigma': 5},
                             'waitparams': {'mu': 50, 'sigma': 15},
                             'costparams': {'ceiling': 2}}})
fTypeArgs1.update({'opportune': {'type_prob': 0.03,
                                'destparams': {'d0': (numpy.array([24, 24]), numpy.array([[4, 0], [0,4]])),
                                               'd1': (numpy.array([10, 35]), numpy.array([[5, 0], [0, 5]])),
                                               'd2': (numpy.array([40, 15]), numpy.array([[5, 0], [0, 5]]))},
                                'waitparams': {'tau': 35},
                                'costparams': {'min': 1, 'max': 4}}})
fTypeArgs1.update({'random': {'type_prob': 0.02,
                             'destparams': None,
                             'waitparams': {'min': 10, 'max': 60},
                             'costparams': {'min': 100, 'max': 1000}}})

fTypeArgs2 = {'normal': {'type_prob': 0.33,
                        'destparams': {'d0': (numpy.array([24, 24]), numpy.array([[6, 0], [0,6]])),
                                       'd1': (numpy.array([15, 40]), numpy.array([[10, 0], [0, 10]])),
                                       'd2': (numpy.array([40, 15]), numpy.array([[10, 0], [0, 10]]))},
                        'waitparams': {'mu': 30, 'sigma': 10},
                        'costparams': {'a': 2, 'b': 4}}}
fTypeArgs2.update({'rich': {'type_prob': 0.4,
                           'destparams': {'d0': (numpy.array([24, 24]), numpy.array([[6, 0], [0,6]]), 1.0),
                                          'd1': (numpy.array([15, 40]), numpy.array([[10, 0], [0, 10]]), 1.0),
                                          'd2': (numpy.array([40, 15]), numpy.array([[10, 0], [0, 10]]), 1.0)},
                           'waitparams': {'min': 15, 'max': 60},
                           'costparams': {'a': 2, 'b': 4, 'scale': 20}}})
fTypeArgs2.update({'hurry': {'type_prob': 0.1,
                            'destparams': {'mu': 10, 'sigma': 5},
                            'waitparams': {'tau': 20},
                            'costparams': {'ceiling': 50}}})
fTypeArgs2.update({'budget': {'type_prob': 0.05,
                             'destparams': {'mu': 10, 'sigma': 5},
                             'waitparams': {'mu': 50, 'sigma': 15},
                             'costparams': {'ceiling': 2}}})
fTypeArgs2.update({'opportune': {'type_prob': 0.1,
                                'destparams': {'d0': (numpy.array([24, 24]), numpy.array([[4, 0], [0,4]])),
                                               'd1': (numpy.array([10, 35]), numpy.array([[5, 0], [0, 5]])),
                                               'd2': (numpy.array([40, 15]), numpy.array([[5, 0], [0, 5]]))},
                                'waitparams': {'tau': 35},
                                'costparams': {'min': 1, 'max': 4}}})
fTypeArgs2.update({'random': {'type_prob': 0.02,
                             'destparams': None,
                             'waitparams': {'min': 10, 'max': 60},
                             'costparams': {'min': 100, 'max': 1000}}})

fTypeArgs3 = {'normal': {'type_prob': 0.1,
                        'destparams': {'d0': (numpy.array([24, 24]), numpy.array([[6, 0], [0,6]])),
                                       'd1': (numpy.array([15, 40]), numpy.array([[10, 0], [0, 10]])),
                                       'd2': (numpy.array([40, 15]), numpy.array([[10, 0], [0, 10]]))},
                        'waitparams': {'mu': 30, 'sigma': 10},
                        'costparams': {'a': 2, 'b': 4}}}
fTypeArgs3.update({'rich': {'type_prob': 0.02,
                           'destparams': {'d0': (numpy.array([24, 24]), numpy.array([[6, 0], [0,6]]), 1.0),
                                          'd1': (numpy.array([15, 40]), numpy.array([[10, 0], [0, 10]]), 1.0),
                                          'd2': (numpy.array([40, 15]), numpy.array([[10, 0], [0, 10]]), 1.0)},
                           'waitparams': {'min': 15, 'max': 60},
                           'costparams': {'a': 2, 'b': 4, 'scale': 20}}})
fTypeArgs3.update({'hurry': {'type_prob': 0.2,
                            'destparams': {'mu': 10, 'sigma': 5},
                            'waitparams': {'tau': 20},
                            'costparams': {'ceiling': 50}}})
fTypeArgs3.update({'budget': {'type_prob': 0.65,
                             'destparams': {'mu': 10, 'sigma': 5},
                             'waitparams': {'mu': 50, 'sigma': 15},
                             'costparams': {'ceiling': 2}}})
fTypeArgs3.update({'opportune': {'type_prob': 0.01,
                                'destparams': {'d0': (numpy.array([24, 24]), numpy.array([[4, 0], [0,4]])),
                                               'd1': (numpy.array([10, 35]), numpy.array([[5, 0], [0, 5]])),
                                               'd2': (numpy.array([40, 15]), numpy.array([[5, 0], [0, 5]]))},
                                'waitparams': {'tau': 35},
                                'costparams': {'min': 1, 'max': 4}}})
fTypeArgs3.update({'random': {'type_prob': 0.02,
                             'destparams': None,
                             'waitparams': {'min': 10, 'max': 60},
                             'costparams': {'min': 100, 'max': 1000}}})

fGenDefault = {'fare_probability': fareProbNormal}

# ------------------------
# Junctions
# ------------------------
import networld as _nw  # only for junctionDef/streetDef signatures

jct0 = _nw.junctionDef(x=0, y=0, cap=2, canStop=True, src=trafficSrcMinor, sink=trafficSinkMinor, **fTypeArgs1)
jct1 = _nw.junctionDef(x=20, y=0, cap=2, canStop=True, src=trafficSrcSignificant, sink=trafficSinkMinor, **fTypeArgs1)
jct2 = _nw.junctionDef(x=40, y=0, cap=2, canStop=True, src=trafficSrcMajor, sink=trafficSinkMajor, **fTypeArgs2)
jct3 = _nw.junctionDef(x=49, y=0, cap=2, canStop=True, src=trafficSrcMinor, sink=trafficSinkMinor, **fTypeArgs2)
jct4 = _nw.junctionDef(x=0, y=10, cap=2, canStop=True, src=trafficSrcSignificant, sink=trafficSinkMinor, **fTypeArgs2)
jct5 = _nw.junctionDef(x=10, y=10, cap=2, canStop=True, fareProb=fareProbSemiPopular, maxTraffic=12, **fTypeArgs2)
jct6 = _nw.junctionDef(x=20, y=10, cap=2, canStop=True, maxTraffic=12, **fTypeArgs2)
jct7 = _nw.junctionDef(x=24, y=15, cap=4, canStop=True, fareProb=fareProbSemiPopular, maxTraffic=12, **fTypeArgs3)
jct8 = _nw.junctionDef(x=30, y=15, cap=4, canStop=True, fareProb=fareProbSemiPopular, maxTraffic=12, **fTypeArgs1)
jct9 = _nw.junctionDef(x=40, y=15, cap=4, canStop=True, fareProb=fareProbPopular, maxTraffic=12, **fTypeArgs1)
jct10 = _nw.junctionDef(x=49, y=15, cap=2, canStop=True, src=trafficSrcSignificant, sink=trafficSinkSignificant, **fTypeArgs1)
jct11 = _nw.junctionDef(x=10, y=20, cap=2, canStop=True, **fTypeArgs2)
jct12 = _nw.junctionDef(x=20, y=20, cap=4, canStop=True, fareProb=fareProbSemiPopular, maxTraffic=12, **fTypeArgs2)
jct13 = _nw.junctionDef(x=10, y=24, cap=2, canStop=True, **fTypeArgs2)
jct14 = _nw.junctionDef(x=20, y=24, cap=4, canStop=True, **fTypeArgs2)
jct15 = _nw.junctionDef(x=24, y=24, cap=8, canStop=True, fareProb=fareProbMagnet, maxTraffic=16, src=trafficSrcHub, sink=trafficSinkMajor, **fTypeArgs1)
jct16 = _nw.junctionDef(x=30, y=24, cap=4, canStop=True, **fTypeArgs1)
jct17 = _nw.junctionDef(x=0, y=35, cap=2, canStop=True, src=trafficSrcSignificant, sink=trafficSinkMajor, **fTypeArgs1)
jct18 = _nw.junctionDef(x=10, y=35, cap=4, canStop=True, fareProb=fareProbPopular, maxTraffic=12, **fTypeArgs2)
jct19 = _nw.junctionDef(x=20, y=30, cap=4, canStop=True, fareProb=fareProbSemiPopular, **fTypeArgs2)
jct20 = _nw.junctionDef(x=24, y=35, cap=4, canStop=True, fareProb=fareProbPopular, maxTraffic=12, src=trafficSrcMajor, sink=trafficSinkDrain, **fTypeArgs1)
jct21 = _nw.junctionDef(x=30, y=30, cap=4, canStop=True, **fTypeArgs3)
jct22 = _nw.junctionDef(x=40, y=30, cap=4, canStop=True, fareProb=fareProbSemiPopular, maxTraffic=12, **fTypeArgs3)
jct23 = _nw.junctionDef(x=49, y=30, cap=2, canStop=True, src=trafficSrcMinor, sink=trafficSinkMinor, **fTypeArgs1)
jct24 = _nw.junctionDef(x=10, y=40, cap=2, canStop=True, **fTypeArgs1)
jct25 = _nw.junctionDef(x=15, y=40, cap=4, canStop=True, fareProb=fareProbPopular, maxTraffic=12, **fTypeArgs1)
jct26 = _nw.junctionDef(x=30, y=40, cap=4, canStop=True, fareProb=fareProbSemiPopular, maxTraffic=12, **fTypeArgs3)
jct27 = _nw.junctionDef(x=40, y=40, cap=2, canStop=True, maxTraffic=12, **fTypeArgs3)
jct28 = _nw.junctionDef(x=0, y=49, cap=2, canStop=True, src=trafficSrcMinor, sink=trafficSinkMinor, **fTypeArgs1)
jct29 = _nw.junctionDef(x=15, y=49, cap=2, canStop=True, src=trafficSrcSignificant, sink=trafficSinkMajor, **fTypeArgs1)
jct30 = _nw.junctionDef(x=30, y=49, cap=2, canStop=True, src=trafficSrcMinor, sink=trafficSinkMinor, **fTypeArgs3)
jct31 = _nw.junctionDef(x=49, y=49, cap=2, canStop=True, src=trafficSrcMinor, sink=trafficSinkMinor, **fTypeArgs3)

junctions = [jct0,jct1,jct2,jct3,jct4,jct5,jct6,jct7,jct8,jct9,jct10,jct11,jct12,jct13,jct14,jct15,
             jct16,jct17,jct18,jct19,jct20,jct21,jct22,jct23,jct24,jct25,jct26,jct27,jct28,jct29,jct30,jct31]
junctionIdxs = [(node.x,node.y) for node in junctions]

# ------------------------
# Streets
# ------------------------
strt0 = _nw.streetDef((0,0), (10,10), 3, 7, biDirectional=True)
strt1 = _nw.streetDef((0,10),(10,10), 2, 6, biDirectional=True)
strt2 = _nw.streetDef((0,35), (10,35), 2, 6, biDirectional=True)
strt3 = _nw.streetDef((0,49), (10,40), 1, 5, biDirectional=True)
strt4 = _nw.streetDef((10,10), (10,20), 4, 0, biDirectional=True)
strt5 = _nw.streetDef((10,20), (10,24), 4, 0, biDirectional=True)
strt6 = _nw.streetDef((10,24), (10,35), 4, 0, biDirectional=True)
strt7 = _nw.streetDef((10,35), (10,40), 4, 0, biDirectional=True)
strt8 = _nw.streetDef((10,10), (20,10), 2, 6, biDirectional=True)
strt9 = _nw.streetDef((10,20), (20,20), 2, 6, biDirectional=True)
strt10 = _nw.streetDef((10,24), (20,24), 2, 6, biDirectional=True)
strt11 = _nw.streetDef((10,35), (20,30), 1, 5, biDirectional=True)
strt12 = _nw.streetDef((10,35), (15,40), 3, 7, biDirectional=True)
strt13 = _nw.streetDef((10,40), (15,40), 2, 6, biDirectional=True)
strt14 = _nw.streetDef((20,0), (20,10), 4, 0, biDirectional=True)
strt15 = _nw.streetDef((20,10), (20,20), 4, 0, biDirectional=True)
strt16 = _nw.streetDef((20,20), (20,24), 4, 0, biDirectional=True)
strt17 = _nw.streetDef((20,24), (20,30), 4, 0, biDirectional=True)
strt18 = _nw.streetDef((15,40), (15,49), 4, 0, biDirectional=True)
strt19 = _nw.streetDef((20,10), (24,15), 3, 7, biDirectional=True)
strt20 = _nw.streetDef((20,20), (24,15), 1, 5, biDirectional=True)
strt21 = _nw.streetDef((20,20), (24,24), 3, 7, biDirectional=True)
strt22 = _nw.streetDef((20,24), (24,24), 2, 6, biDirectional=True)
strt23 = _nw.streetDef((20,30), (24,24), 1, 5, biDirectional=True)
strt24 = _nw.streetDef((20,30), (24,35), 3, 7, biDirectional=True)
strt25 = _nw.streetDef((15,40), (24,35), 1, 5, biDirectional=True)
strt26 = _nw.streetDef((15,40), (30,40), 2, 6, biDirectional=True)
strt27 = _nw.streetDef((24,15), (24,24), 4, 0, biDirectional=True)
strt28 = _nw.streetDef((24,24), (24,35), 4, 0, biDirectional=True)
strt29 = _nw.streetDef((24,15), (30,15), 2, 6, biDirectional=True)
strt30 = _nw.streetDef((24,24), (30,15), 1, 5, biDirectional=True)
strt31 = _nw.streetDef((24,24), (30,24), 2, 6, biDirectional=True)
strt32 = _nw.streetDef((24,24), (30,30), 3, 7, biDirectional=True)
strt33 = _nw.streetDef((24,35), (30,30), 1, 5, biDirectional=True)
strt34 = _nw.streetDef((24,35), (30,40), 3, 7, biDirectional=True)
strt35 = _nw.streetDef((30,15), (30,24), 4, 0, biDirectional=True)
strt36 = _nw.streetDef((30,24), (30,30), 4, 0, biDirectional=True)
strt37 = _nw.streetDef((30,40), (30,49), 4, 0, biDirectional=True)
strt38 = _nw.streetDef((30,15), (40,15), 2, 6, biDirectional=True)
strt39 = _nw.streetDef((30,15), (40,30), 3, 7, biDirectional=True)
strt40 = _nw.streetDef((30,40), (40,40), 2, 6, biDirectional=True)
strt41 = _nw.streetDef((40,0), (40,15), 4, 0, biDirectional=True)
strt42 = _nw.streetDef((40,15), (40,30), 4, 0, biDirectional=True)
strt43 = _nw.streetDef((40,30), (40,40), 4, 0, biDirectional=True)
strt44 = _nw.streetDef((40,15), (49,0), 1, 5, biDirectional=True)
strt45 = _nw.streetDef((40,15), (49,15), 2, 6, biDirectional=True)
strt46 = _nw.streetDef((40,30), (49,30), 2, 6, biDirectional=True)
strt47 = _nw.streetDef((40,40), (49,49), 3, 7, biDirectional=True)

streets = [strt0,strt1,strt2,strt3,strt4,strt5,strt6,strt7,strt8,strt9,strt10,strt11,strt12,strt13,strt14,strt15,
           strt16,strt17,strt18,strt19,strt20,strt21,strt22,strt23,strt24,strt25,strt26,strt27,strt28,strt29,strt30,strt31,
           strt32,strt33,strt34,strt35,strt36,strt37,strt38,strt39,strt40,strt41,strt42,strt43,strt44,strt45,strt46,strt47]
