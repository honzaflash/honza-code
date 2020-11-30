"""
System module containing the System class which runs the simulation
"""

from _datetime import datetime
import random
from collections import deque
import os
from os import path
from time import sleep

from Human import Human
from Human import NEVER_BEEN_TO, ATTENDING, LEFT, YEAR, REMOVING_AGE_Y


MINIMAL_LEADER_SPIRIT = 300
MINIMAL_LEADER_COUNT = 3


class clubDeadException(ValueError):
    pass


class System:
    """
    The System contains the humans and runs the simulation
    """
    def __init__(self, focus: float, cap: int, people):
        self.focus = focus  # expecting value from <0;1>
        self.cap = cap
        # people shouldn't be bigger than cap
        self.people: deque[Human] = deque(sorted(people, key=(lambda hum: hum.age)))
        self.time = 0
        self.clubDead = False
        self.clubJoined = [ 0 for _ in range(REMOVING_AGE_Y + 5) ] # 5 is just room for error and whoopsies
        self.clubLeft = [ 0 for _ in range(REMOVING_AGE_Y + 5)]
        self.sundayLost = 0 # people who leave and don't go to sunday services
        self.sundayJoined = 0

    def clubCount(self):
        return len(list(filter(lambda h: h.club(), self.people)))

    def sundayCount(self):
        return len(list(filter(lambda h: h.sunday(), self.people)))

    def leftActually(self, left):
        leftButInChurch = len(list(filter(lambda hmn: hmn.sunay() and hmn.club_ == LEFT, self.people)))
        return left - leftButInChurch

    def averageClubSpirit(self):
        total = 0
        count = 0
        for hmn in self.people:
            if hmn.club():
                total += hmn.spirit
                count += 1
        if not count:
            return 0
        return total / count

    def printUpdate(self):
        print(" (total people count: ", len(self.people), ")")
        stats = {NEVER_BEEN_TO: 0, ATTENDING: 0, LEFT: 0, "church": 0}
        for hmn in self.people:
            stats[hmn.club_] += 1
            if hmn.sunday():
                stats["church"] += 1
        print("no: ", stats[NEVER_BEEN_TO], ", yes: ", stats[ATTENDING], ", left: ", stats[LEFT],
              ", church: ", stats["church"], sep="")

    def log(self, file):
        stats = {NEVER_BEEN_TO: 0, ATTENDING: 0, LEFT: 0, "church": 0}
        for hmn in self.people:
            stats[hmn.club_] += 1
            if hmn.sunday():
                stats["church"] += 1
        file.write(f'{self.time // YEAR},{stats[NEVER_BEEN_TO]},{stats[ATTENDING]},{stats[LEFT]},{stats["church"]},'
                   f'{self.averageClubSpirit()},\n')

    def logHeader(self, file):
        file.write(f'focus:,{self.focus}\n'
                   "year,never been,attending,left,church,spirit,died?\n")

    def invitePeople(self):
        youngstersOnly = list(filter(
                lambda h: h.age < 9 * YEAR and h.club_ == NEVER_BEEN_TO,
                self.people))  #  ^^^^^^^^ = (24 - <age offset>) * <weeks in a year>
        if youngstersOnly:
            return random.choice(youngstersOnly).getInvited(self.focus)
        return -1

    def step(self, verbose=False, logFile=None):
        prev_c = self.sundayCount()
        for hmn in self.people:
            # incrementing spirit
            hmn.increment(self.focus)
            # members of club inviting other people
            if hmn.club():
                maybeAge = self.invitePeople()
                if maybeAge != -1:
                    self.clubJoined[maybeAge // YEAR] += 1
                if hmn.maybeLeave(self.focus):
                    # people maybe leaving the club
                    self.clubLeft[hmn.age // YEAR] += 1
                    self.sundayLost += int(not hmn.sunday())
        self.sundayJoined += self.sundayCount() - prev_c

        self.time += 1
        # every year add and remove people
        if self.time % YEAR == 0:
            for _ in range(self.cap // REMOVING_AGE_Y):
                self.people.pop()
                self.people.appendleft(Human())

        if verbose:
            self.printUpdate()
        if logFile:
            self.log(logFile)

        if len(list(filter(lambda h: h.spirit > MINIMAL_LEADER_SPIRIT, self.people)))\
                < MINIMAL_LEADER_COUNT:
            self.clubDead = True
            raise clubDeadException


    def run(self, steps, verbosity=0, log=False, logDir="output_model_data/"):
        original_club = self.clubCount()
        original_sunday = self.sundayCount()
        if verbosity > 0:
            print()
            self.printUpdate()
        logFile = None
        try:
            if log:
                logFile = openNewLog(logDir, "f" + ("%.3f" % (self.focus / 10))[2:])
                self.logHeader(logFile)
            for _ in range(steps):
                self.step(verbosity > 1, logFile)
        except clubDeadException:
            if log:
                logFile.write(f'{self.time // YEAR},0,0,0,0,0,club is dead\n')
            if verbosity < 1:
                return
            print("--- club is dead ---")
        finally:
            if logFile:
                logFile.close()
        if verbosity < 1:
            return
        print("after ", self.time // YEAR, " years ", self.time % YEAR, " weeks" )
        self.printUpdate()
        print("### progress made:")
        print("club size difference: ", self.clubCount() - original_club,
              "; sunday difference: ", self.sundayCount() - original_sunday)
        print("club joined total: ", sum(self.clubJoined))
        print(f'avg age of joining club: {wAvg(self.clubJoined)}')
        print(f'avg age of leaving club: {wAvg(self.clubLeft)}')
        print("didn't join sunday total: ", self.sundayLost)
        print("sunday joined total: ", self.sundayJoined)



def wAvg(itr: iter):
    total = 0
    for i in range(len(itr)):
        total += i * itr[i]
    if sum(itr) == 0:
        return 0
    return total / sum(itr)


def uniqueCsvPath(path):
    i = 1
    while os.path.exists(path + str(i) + ".csv"):
        i += 1
    return path + str(i) + ".csv"


def openNewLog(targetPath, desc: str):
    if not path.exists(targetPath):
        os.mkdir(targetPath)
    name = targetPath + "log-" + desc + datetime.today().strftime("-%m-%d_%H-%M_")
    i = 1
    name = uniqueCsvPath(name)
    for _ in range(10):
        try:
            return open(name, "w")
        except Exception as e:
            import sys
            print(e, file=sys.stderr)
            sleep(0.5)  # yay polling!

