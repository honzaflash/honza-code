import random

from Human import REMOVING_AGE_Y, AGE_OFFSET_Y, Human, YEAR
from System import System


def simplePopInit(population = 200):
    peeps = []
    count = 0
    while (count < 12 or 20 < count):
        peeps = []
        for year in range(REMOVING_AGE_Y):
            for _ in range(population // REMOVING_AGE_Y):
                club = int(year < (22 - AGE_OFFSET_Y) and not random.randint(0, 6))
                sunday = int((23 - AGE_OFFSET_Y) < year and not random.randint(0, 8))
                spirit = 0
                if sunday:
                    spirit = random.randint(600, 1000)
                if club:
                    spirit = random.betavariate(0.8, 3) * 1000
                peeps.append(Human(year * YEAR, spirit, club))
        count = len(list(filter(lambda h: h.club(), peeps)))
    return peeps


def betterPopInit(focus = 0.5, pop_size = 200):
    peeps = simplePopInit(pop_size)
    count = len(list(filter(lambda h: h.club(), peeps)))
    while (count < 14 or 22 < count):
        peeps = simplePopInit(pop_size)
        count = len(list(filter(lambda h: h.club(), peeps)))
    s = System(focus, pop_size, peeps)
    s.run(10 * YEAR, 1)
    return s.people