from enum import Enum
from typing import Tuple, Union
from Entities import Entity


class TileType(Enum):
    EMPTY = 0
    WALL = 1


class Tile:
    def __init__(self, type: TileType, sprite_id, x, y):
        self.type = type
        self.sprite_id = sprite_id
        self.x = x
        self.y = y
        self.content: Union[Entity,None] = None

    def has_content(self):
        return self.content != None

    def get_content(self):
        return self.content

    def set_content(self, content: Union[Entity,None]):
        self.content = content

    def get_origin(self) -> Tuple[int, int]:
        return self.x, self.y

    def get_center(self) -> Tuple[float, float]:
        return self.x + 0.5, self.y + 0.5

    def is_passable(self) -> bool:
        """ :returns: True if the player may traverse this tile """
        if self.type in [TileType.WALL]: return False
        if self.has_content():
            return self.get_content().is_traversable()
        return True
