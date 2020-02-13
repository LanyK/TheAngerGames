from typing import Tuple

class Player:
    def __init__(self, id: int, x: float, y: float, lifes: int, power: int, bombs: int, immortal: bool = False, slimey: bool = False):
        self.id = id
        self.x = x
        self.y = y
        self.inverted_keyboard = False # only for visual purposes
        self.autowalk = False # only for visual purposes
        self.immortal = immortal
        self.slimey = slimey
        self.lifes = lifes
        self.power = power
        self.bombs = bombs
        self.facing = 0
        self.anger = 0.
        self.bloody = 0

    def get_pos(self) -> Tuple[float,float]:
        return (self.x,self.y)

    def set_anger(self,anger:float):
        self.anger = anger

class PlayerHistory(object):
    """ Stores past player movements and actions to let the view pick the right animations
    """

    def __init__(self):
        self.stood_still = True
        self.last_facing = 0
        self.last_x = 0
        self.last_y = 0

    def stands_still(self, new_x, new_y):
        return self.last_x == new_x and self.last_y == new_y

    def update(self, x, y, facing, stood_still=True):
        self.last_x = x
        self.last_y = y
        self.last_facing = facing
        self.stood_still = stood_still
