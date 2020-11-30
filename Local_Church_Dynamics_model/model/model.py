"""
functions in this module are meant to be used to produce the data for analysis

here we have functions for running batches of simulations
and logging the data + few helper functions
executable and can also be imported

the state is functional but some refactoring could be done
even some functions have room left for expansion

author: Jan Rychlý
"""

import os
import random
from copy import deepcopy

from System import System, wAvg, uniqueCsvPath
from Human import YEAR, LEFT
from populationInitializers import simplePopInit


def demo(years=40, focus=0.5, out="console"):
    peeps = simplePopInit()
    # print("initial club members:")   # print the club members
    # print(list(map(str, filter(lambda h: h.club(), peeps))))
    s = System(focus, 200, peeps)
    if out == "console":
        s.run(YEAR * years, 2)
    elif out == "log":
        s.run(YEAR * years, 1, log=True)
    elif out == "both":
        s.run(YEAR * years, 2, log=True)
    elif out == "silent":
        s.run(YEAR * years, 1)
    else:
        print("invalid option:", out)


def bulkRuns(focus=0.5, each_run=3, verbosity=0, samples=40, initializer=simplePopInit, log=False):
    record = [[], []]
    for i in range(samples):
        peeps = initializer()
        s = System(focus, 200, peeps)
        s.run(each_run * YEAR, verbosity, log)
        record[0].append(sum(s.clubJoined))
        record[1].append(len(list(filter(lambda h: h.club_ == LEFT, s.people))))
        if verbosity < 1:
            print("-", end=("\n" if i % 60 == 59 else ""), flush=True)
    if len(record[0]) == 0:
        print(" 0 samples ")
        return
    print()
    print(" average joining club members per year: ", sum(record[0]) / len(record[0]) / each_run,
          "; median: ", sorted(record[0])[len(record[0])//2] / each_run, sep="")
    print("      average members leaving per year:", sum(record[1]) / len(record[1]) / each_run)


def largeTimeScaleSensitivity(years=80, samples=1, startF=0, endF=101, granularity=10):
    # data generated is the state of the model at the end - not an average of values over 1 year
    path = "output_model_data/long_term_convergence/"
    if not os.path.exists(path):
        os.mkdir(path)

    if startF < 0: startF = int(0)
    if endF > 101: endF = int(101)

    ys = [40 for _ in range(years // 40)]
    if years % 40:
        ys.append(years % 40)
    outs = [open(uniqueCsvPath(path + "sum_log-Y%03dy%03d_s%d_" % (years, sum(ys[:n+1]), samples)), "w")
            for n in range(len(ys))]

    for f in outs:
        f.write("focus,year,never been,attending,left,church,spirit,\n")

    for _ in range(len(range(startF, endF, granularity)) * samples):
        print("_", end="")
    print(flush=True)

    ppl = simplePopInit() # or -> betterPopInit()
    for f in range(startF, endF, granularity):
        for _ in range(samples):
            s = System(f / 100, 200, deepcopy(ppl))
            for o, y in zip(outs, ys):
                s.run(y * YEAR, verbosity=0)
                o.write(f'{s.focus},')
                s.log(o)
            print("\u2588", end="", flush=True)


def avgXOverFocus(totalSamples=50, startF=0, endF=101, extra=False):
    path = "output_model_data/avg_x_over_focus/"
    if not os.path.exists(path):
        os.mkdir(path)

    if startF < 0: startF = int(0)
    if endF > 101: endF = int(101)
    path += "sum_log-f%03d-%03d_s%d_" % (startF, endF - 1, totalSamples)
    i = 1
    while os.path.exists(path + str(i) + ".csv"):
        i += 1
    path += str(i) + ".csv"
    with open(path, "w") as out:
        header = "focus,age_joined,age_left,avg_spirit"
        if extra:
            header += ",church_joined_total,club_joined_total,actually_left_total"
        out.write(header + "\n")

        ppl = simplePopInit()  # or -> betterPopInit()
        for _ in range(totalSamples):
            print("_", end="")
        print(flush=True)
        for _ in range(totalSamples):
            f = random.uniform(startF / 100, (endF - 1) / 100)
            s = System(f, 200, deepcopy(ppl))
            s.run(40 * YEAR, verbosity=0)
            summary = f'{f},{wAvg(s.clubJoined)},{wAvg(s.clubLeft)},{s.averageClubSpirit()}'
            if extra: summary += f',{s.sundayJoined},{sum(s.clubJoined)},{s.leftActually()}'
            out.write(summary + "\n")
            print("\u2588", end="", flush=True)


def focusSensitivity(granularity=10, samples=1, startF=0, endF=101):
    path = "output_model_data/focus_sensitivity_"
    i = 1
    while os.path.exists(path + str(i)):
        i += 1
    path += str(i) + "/"

    if startF < 0: startF = 0
    if endF > 101: endF = 101

    ppl = simplePopInit() # or -> betterPopInit()
    for _ in range(len(range(startF, endF, granularity)) * samples):
        print("_", end="")
    print(flush=True)
    for f in range(startF, endF, granularity):
        for _ in range(samples):
            s = System(f / 100, 200, deepcopy(ppl))
            s.run(40 * YEAR, verbosity=0, log=True, logDir=path)
            print("\u2588", end="", flush=True)



if __name__ == "__main__":
    demo(20, 0.5, out="both")

