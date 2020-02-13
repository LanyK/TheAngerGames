import math

DOWN = 0
RIGHT = 1
UP = 2
LEFT = 3


class Player:
    def __init__(self, box_x: float, box_y: float):
        """
        :param x: initialize x pos of the tile the player stands in
        :param y: initialize y pos of the tile the player stands in
        """
        self.x = box_x + 0.5
        self.y = box_y + 0.5
        self.lifes = 3
        self.base_speed = 0.05
        self.max_bonus_speed = 0.1
        self.speed = self.base_speed  # how far can the player move in one Frame
        self.bombs = 1  # how many bombs can the player place at once
        self.power = 3  # range of explosion in fields TODO make anger-dependant
        self.immortal_ticks = 0  # player needs to be immortal for a short time after he lost a live
        self.slime_cooldown_ticks = 0
        self.facing = DOWN
        self.inverted_ticks = 0
        self.slime = 0
        self.last_action = "down"
        self.autowalk_ticks = 0
        # todo: power?, bombs?

    def get_pos(self):
        return (self.x, self.y)

    def get_tile_pos(self):
        return(int(self.x),int(self.y))

    def move(self, dx: float, dy: float, action=None):
        self.x += dx
        self.y += dy
        if action == "up":
            self.facing = UP
            self.last_action = "up"
        elif action == "down":
            self.facing = DOWN
            self.last_action = "down"
        elif action == "left":
            self.facing = LEFT
            self.last_action = "left"
        elif action == "right":
            self.facing = RIGHT
            self.last_action = "right"

    def invert_action(self, action): # TODO move to Game.py?
        if action == "left":
            action = "right"
            self.last_action = "right"
        elif action == "right":
            action = "left"
            self.last_action = "left"
        elif action == "down":
            action = "up"
            self.last_action = "up"
        elif action == "up":
            action = "down"
            self.last_action = "down"
        return action

    def has_slime_cooldown(self) -> bool:
        return self.slime_cooldown_ticks > 0

    def set_autowalk_time(self, ticks):
        self.autowalk_ticks = ticks

    def is_autowalking(self) -> bool:
        return self.autowalk_ticks > 0

    def is_inverted(self):
        return self.inverted_ticks > 0

    def is_immortal(self):
        return self.immortal_ticks > 0

    def set_immortal_time(self, ticks:int):
        self.immortal_ticks = ticks

    def set_invertion_time(self, ticks):
        self.inverted_ticks = ticks

    def info_dict(self,id):
        """ id: this player's ID """
        return {  "id": id,
                  "x": self.x,
                  "y": self.y,
                  "facing": self.facing,
                  "lifes": self.lifes,
                  "immortal": self.immortal_ticks,
                  "slime": self.slime }
