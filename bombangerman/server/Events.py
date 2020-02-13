from enum import Enum

class EventType(Enum):
    GENERIC = 0
    PLAYER_INIT = 1
    PLAYER_MORTAL = 2
    PLAYER_DAMAGED = 3
    PLAYER_MOVED = 4
    SPAWN_BOX = 5
    SPAWN_BOMB = 6
    SPAWN_EXPLOSION = 7
    UPDATE_TRAP = 8
    REMOVE_BOX = 9
    REMOVE_BOMB = 10
    REMOVE_EXPLOSION = 11
    PLAYER_NOT_SLIMEY = 12
    PLAYER_SLIMED = 13
    WINNER = 14
    SPAWN_FALLING_BOX = 15
    REMOVE_FALLING_BOX = 16
    SPAWN_CRUSHING_BOX = 17
    REMOVE_CRUSHING_BOX = 18
    PLAYER_TAUNT = 19
    SPAWN_POWER_UP = 20
    REMOVE_POWER_UP = 21
    ANGER_INFO = 22
    ACTIVATE_TRAP = 23
    RESET_TRAP = 24
    PLAYER_INVERT_KEYBOARD_ON = 25
    PLAYER_INVERT_KEYBOARD_OFF = 26
    PLAYER_CHANGE_BOMBS_COUNT = 27
    PLAYER_CHANGE_POWER_AMOUNT = 28
    PLAYER_AUTOWALK_ON = 29
    PLAYER_AUTOWALK_OFF = 30


class GameEvent:
    """ Represents a game event to be set to the clients
    """

    def __init__(self, type: EventType, data: dict):
        self.data = data
        self.type = type

    def encode(self) -> tuple:
        """ returns a tuple (type,data_dict) """
        return (self.type.value, self.data)
