from enum import Enum
from typing import Tuple
from math import floor
import random
from Events import GameEvent, EventType

class EntityType(Enum):
    BOX = 0
    BOMB = 1
    SPIKE_TRAP = 2
    EXPLOSION = 3
    FALLING_BOX = 4
    CRUSHING_BOX = 5
    POWER_UP = 6

class PowerUpType(Enum):
    INVERT_KEYBOARD = 0
    AUTOWALK = 1
    POWER_PLUS = 2
    BOMB_PLUS = 3

class Entity:
    """ Represents an object that sits on the map, such as a crate or a bomb.
        This class should not be instanciated directly, instead, one subclass
        is present for each kind of Entity.
    """
    def __init__(self, x, y, ent_type:EntityType):
        self.x = x
        self.y = y
        self.type = ent_type

    def is_of_type(self, type:EntityType):
        return self.type == type

    def get_pos(self) -> Tuple[float,float]:
        """ :returns: (x,y) """
        return self.x,self.y

    def get_tile_pos(self) -> Tuple[int,int]:
        """ :returns: (floor(x),floor(y)) """
        return (int(floor(self.x)),int(floor(self.y)))

class TimerEntity(Entity):
    """ Entity with a timer that can be ticked down via self.tick().
        Check expiration with self.timer_expired() """
    def __init__(self,x,y,type:EntityType,ticks_to_expiration:int):
        super().__init__(x,y,type)
        self.ticks_to_expiration = ticks_to_expiration

    def tick(self) -> None:
        """ Ticks the internal timer down by 1 step """
        self.ticks_to_expiration -= 1

    def timer_expired(self) -> bool:
        """ Returns true if the ticking timer has expired and the bomb should explode """
        return self.ticks_to_expiration <= 0

class Traversable():
    """ Base interface class to provide is_traversable() -> True """
    def __init__(self,*args,**kwargs): # discards any arguments
        pass

    def is_traversable(self):
        return True

class NotTraversable():
    """ Base interface class to provide is_traversable() -> False """
    def __init__(self,*args,**kwargs): # discards any arguments
        pass

    def is_traversable(self):
        return False

class FallingBox(TimerEntity, Traversable):
    """ A falling box. The Tile is still traversable """
    def __init__(self,x,y,ticks_to_expiration):
        super().__init__(x,y,EntityType.FALLING_BOX,ticks_to_expiration)

class CrushingBox(TimerEntity, NotTraversable):
    """ A box so close to the ground that it smashes the player. Not traversable. """
    def __init__(self,x,y,ticks_to_expiration):
        super().__init__(x,y,EntityType.CRUSHING_BOX,ticks_to_expiration)

class Box(Entity, NotTraversable):
    """ Represents an impassable, destructible Box object. """
    def __init__(self,x,y):
        super().__init__(x,y,EntityType.BOX)

class Explosion(TimerEntity, Traversable):
    """ Represents an passable explosion object. """
    def __init__(self,x,y,ticks_to_expiration):
        super().__init__(x,y,EntityType.EXPLOSION, ticks_to_expiration)

class Bomb(TimerEntity, NotTraversable):
    """ Represents a bomb about to explode """
    def __init__(self,x,y,power,owner_id,ticks_to_explosion):
        super().__init__(x,y,EntityType.BOMB,ticks_to_explosion)
        self.power = power
        self.owner_id = owner_id

    def get_owner_id(self):
        return self.owner_id

    def get_power(self) -> int:
        return self.power

class PowerUp(Entity, Traversable):
    """ Represents a collectable power-Up item on the ground """
    def __init__(self, x, y, power_up_type:PowerUpType):
        super().__init__(x,y,EntityType.POWER_UP)
        self.power_up_type = power_up_type

    def get_power_up_type(self) -> PowerUpType:
        return self.power_up_type


class SpikeTrap(Entity, Traversable):
    """ A Trap is a tile that periodically spawns an effect that can kill players """
    def __init__(self,x,y,min_delay_ticks,max_delay_ticks,active_ticks=1,armed=True):
        super().__init__(x,y,EntityType.SPIKE_TRAP)
        self.min_delay_ticks = min_delay_ticks
        self.max_delay_ticks = max_delay_ticks
        self.delay_delta = max_delay_ticks - min_delay_ticks
        self.activation_duration = active_ticks
        self.activation_ticks_remaining = -1
        self.armed = armed
        self.ticks_to_activation = max_delay_ticks
        self.reset_delay()

    def info_dict(self):
        """ x: the x pos of this trap
            y: the y pos of this trap
        """
        return {"x":self.x,"y":self.y,"ticks":self.ticks_to_activation,"active":self.is_active()}

    def tick(self, game) -> None:
        """ Ticks down the timers of this trap.
            if is_active:
                ticks down remaining active time
            else if is_armed:
                ticks down remaining time to activation
        """
        if self.activation_ticks_remaining > 0:
            self.activation_ticks_remaining -= 1
            if self.activation_ticks_remaining == 0:
                self.reset_delay(mode="random")
                game.register_event(GameEvent(EventType.RESET_TRAP, {"x": self.x, "y": self.y, "t": self.ticks_to_activation}))
        elif self.armed:
            self.ticks_to_activation -= 1

    def reset_delay(self,mode="random") -> None:
        """ :param mode: one of "min" "max" "random". Defaults to "random"
        """
        if mode == "min":
            self.ticks_to_activation = self.min_delay_ticks
        elif mode == "max":
            self.ticks_to_activation = self.max_delay_ticks
        elif mode == "random":
            self.ticks_to_activation = int(self.min_delay_ticks + (random.random() * self.delay_delta))
        else:
            raise NotImplementedError("reset_delay has mode",mode,"not implemented!")

    def is_active(self):
        return self.activation_ticks_remaining > 0

    def activate(self):
        self.activation_ticks_remaining = self.activation_duration
        self.ticks_to_activation = 1

    def handle_damage(self, players:list, game):
        """ :param players: A list of Player objects """
        tx, ty = self.get_tile_pos()
        for id, player in enumerate(players):
            if not player.is_immortal():
                px,py = player.get_pos()
                if floor(px) == tx and floor(py) == ty:
                    player.lifes -= 1
                    player.set_immortal_time(200)
                    game.register_event(GameEvent(EventType.PLAYER_DAMAGED, {"id": id, "dmg": 1}))

    def set_is_armed(self, is_armed:bool=True) -> None:
        self.armed = is_armed

    def is_armed(self) -> bool:
        return self.armed

    def should_activate(self) -> bool:
        return self.ticks_to_activation <= 0
