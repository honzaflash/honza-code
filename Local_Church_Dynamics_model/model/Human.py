"""
Human module containing the Human class for representing agents in the model
"""
from math import exp
import random


# janky state "enum" constants
NEVER_BEEN_TO = 0
ATTENDING = 1
LEFT = 2

# time constants
YEAR = 52
AGE_OFFSET_Y = 15
# STARTING_AGE = 0      in reality 15
REMOVING_AGE_Y = 21   # in reality 36


def humanReadableAge( age ):
    return (age // YEAR + AGE_OFFSET_Y, age % YEAR)


"""
parametrisation of increments and probabilities
"""
#spirit score increment for attending church
SUNDAY_SERVICE_INCREMENT = 2

# spirit score increment function for attending youth group
def spiritIncrement(club_focus):
    return 2 * club_focus

# generator for spirit score at which a person starts attending sunday services
def sundayAttendanceDistribution():
    return random.betavariate(7, 7) * 700
    # behaviour should be similar to random.gauss() it is not used bc I didn't notice it existed



class Human:
    """
    The Human class! represents an agent that has several states:
        regarding church youth club:
            has never been there,
            is attending,
            used to attend but left (and can't go back);
        regarding church sunday service:
            has never attended,
            is attending
    agents also age and gain spirit score (grow spiritually)
    """
    def __init__(self, age = random.randint(0, 51), spirit_ = 0, club_ = 0):
        self.age = age
        self.spirit = int(spirit_)
        self.club_ = club_  # youth group - None (hasn't been invited) -> True (attending) -> False (left)
        self.join_sunday_at = sundayAttendanceDistribution()  # spirit at which a person will join sunday services

    def club(self):
        return self.club_ == ATTENDING

    def sunday(self):
        return self.join_sunday_at < self.spirit

    def increment(self, club_focus):
        self.age += 1
        if self.club():
            self.spirit += spiritIncrement(club_focus)
        if self.sunday():
            self.spirit += SUNDAY_SERVICE_INCREMENT

    def getInvited(self, club_focus):
        TWEAKING_CONSTANT = 90  # the higher the less probable joining is
        # logistic function - k...exponent coefficient; midpoint is 4 (real age of ~19)
        ageMult = lambda k: 1 / (1 + exp( k * (4 - self.age / YEAR) ) )
        if (self.club() == NEVER_BEEN_TO and
                random.random() * TWEAKING_CONSTANT <
                ( ageMult(-0.8) * (1 - club_focus) ) + ( 0.3 * ageMult(1) * club_focus) ):
                # (^^^   fun focused part    ^^^)      (^^^ spiritually focused part ^^^)
                # the magic numbers are here only to provide a specific shape of the graph
                # formula returns values between 0 and 1
            self.club_ = ATTENDING
            return self.age
        return -1

    def maybeLeave(self, club_focus):
        TWEAKING_CONSTANT = 1000 # the higher the less probable leaving is
        # logistic function - k...exponent coefficient; m...midpoint
        ageMult = lambda k, m: 10 / (1 + exp( k * (m - self.age / YEAR) ) )
        if (random.random() * TWEAKING_CONSTANT <
                (self.spirit / 100 + 1)**(-0.5) *  # higher spirit score weakens the chances of leaving
                (1.5 * ageMult(0.4, 10) * (1 - club_focus) + (2 * ageMult(-0.3, 0) + 0.3)  * club_focus**2 ) ):
                # (^^^      fun focused part      ^^^)         (^^^     spiritually focused part     ^^^)
                # similarly also here the magic numbers are constants providing specific shape of the graph
                # this formula can return values up to 15 - hence the major difference in the two tweaking constants
            self.club_ = LEFT
            # if not attending sunday service, person will be counted as "lost"
            return True
        return False

    def __str__(self):
        if self.club_ == NEVER_BEEN_TO:
            club = "no"
        elif self.club_ == ATTENDING:
            club = "yes"
        else:
            club = "left"
        if self.sunday():
            sunday = "yes"
        else:
            sunday = "no"
        return "Human {age: " + str(humanReadableAge(self.age)[0]) + \
                 "; spirit: " + str(self.spirit) + \
                   "; club: " + club + \
                 "; sunday: " + sunday + " }"


