from Player import Player
from math import floor
from collections import deque
import pygame
import random
from typing import Optional, List
import json
from Events import EventType, GameEvent
from Entities import *
from Tiles import TileType, Tile
from Schedulers import FallingBoxScheduler, PowerUpScheduler

# fraction. 0.0 -> never slide, 1.0 always slide.
# FRONTAL_SLIDE_THRESHOLD only handles slide when the frontal tile is solid
# Slides upon entering open frontal tiles along corners of diagonally adjacent walls
# are not handled by this threshold but instead always happen on collision with the corner.
FRONTAL_SLIDE_THRESHOLD_FACTOR = 0.1

PLAYER_RADIUS = 0.3  # Collision radius, must be 0 < x < 0.5!

# used in sliding detection for FRONTAL_SLIDE_THRESHOLD
# minimum sideways player distance from tile center
MIN_PLAYER_SIDE_OFFSET = (0.5 - PLAYER_RADIUS) ** 2
# maximum sideways player distance from tile center
MAX_PLAYER_SIDE_OFFSET = (0.5 ** 2) + ((0.5 - PLAYER_RADIUS) ** 2)
# If the player is further away from the tile center than this, sliding will happen upon frontal collision
FRONTAL_SLIDE_THRESHOLD = ((
                                   MAX_PLAYER_SIDE_OFFSET - MIN_PLAYER_SIDE_OFFSET) * FRONTAL_SLIDE_THRESHOLD_FACTOR) + MIN_PLAYER_SIDE_OFFSET

DIR = {"right": (1, 0),
       "left": (-1, 0),
       "up": (0, -1),
       "down": (0, 1)}

# diag_left, diag_right, left, right
TILE_OFFSETS = {
    (1, 0): ((1, -1), (1, 1), (0, -1), (0, 1)),
    (0, 1): ((1, 1), (-1, 1), (1, 0), (-1, 0)),
    (-1, 0): ((-1, 1), (-1, -1), (0, 1), (0, -1)),
    (0, -1): ((-1, -1), (1, -1), (-1, 0), (1, 0)),
}

RIGHT_CORNER_OFFSETS = {
    (1, 0): (0, 0),
    (0, 1): (+1, 0),
    (-1, 0): (+1, +1),
    (0, -1): (0, +1),
}

LEFT_CORNER_OFFSETS = {
    (1, 0): (0, +1),
    (0, 1): (0, 0),
    (-1, 0): (+1, 0),
    (0, -1): (+1, +1),
}

SLIDE_FACTORS = {
    (1, 0): {"left": (0, -1), "right": (0, +1)},
    (0, 1): {"left": (1, 0), "right": (-1, 0)},
    (-1, 0): {"left": (0, +1), "right": (0, -1)},
    (0, -1): {"left": (-1, 0), "right": (+1, 0)}
}

TIME_TILL_EXPLOSION = 60 * 5 # TODO export configs into a config file
EXPLOSION_DURATION = 60
CRUSHING_BOX_DURATION = 20

TAUNT_DURATION = 60 * 4
INVERTED_KEYBOARD_TICKS = 60 * 10
AUTOWALK_TICKS = 60 * 10
SLIME_COOLDOWN = 60 * 30

ANGER_HISTORY_LEN = 400
ANGER_HISTORY_DECAY_FACTOR = 1/ANGER_HISTORY_LEN
ANGER_INPUT_RETENTION_TICKS = 18

class Game:
    def __init__(self, width: int = 15, height: int = 16, file=None):
        """
        :param width: width of the game in Boxes
        :param height: height of the game in Boxes
        :param file: file from where a game floor should be loaded
        """
        self.width: int = width
        self.height: int = height
        self.players: list = []
        self.tiles: list = [[0 for _ in range(self.height)] for _ in range(self.width)]
        self.starts: list = []
        self.bombs: List[Bomb] = []  # TODO couple entities into a single interface and list
        self.explosions: List[Explosion] = []
        self.falling_boxes: List[FallingBox] = []
        self.crushing_boxes: List[CrushingBox] = []
        self.spike_traps: list = []
        self.field_version: int = 0
        self.winner: Optional[int] = None
        self.events: list = [deque(), deque()]
        self.raw_angers: List[float] = [0.,0.]
        self.aggregated_angers: List[float] = [0.,0.]
        self.anger_histories: Tuple[List[float],List[float]] = ([0. for _ in range(ANGER_HISTORY_LEN)],[0. for _ in range(ANGER_HISTORY_LEN)])
        self.anger_history_max = self.precompute_anger_history_max()
        self.anger_retention_container = [[0,0.],[0,0.]] # counter,anger_val

        self.falling_box_scheduler = FallingBoxScheduler(spawn_rate=0.015, grace_period_ticks=180, allow_spawn_on_player=True)

        self.power_up_scheduler = PowerUpScheduler(spawn_rate=0.15, grace_period_ticks=0, relative_spawn_rates={PowerUpType.AUTOWALK: 0.9, PowerUpType.INVERT_KEYBOARD: 1.0, PowerUpType.POWER_PLUS: 0.1, PowerUpType.BOMB_PLUS: 0.2})

        if file is None:
            # Build upper wall-tops
            self.tiles[0][0] = Tile(TileType.WALL, 33, 0, 0)
            self.tiles[-1][0] = Tile(TileType.WALL, 36, 0, 0)
            for x in range(1, self.width - 1):
                self.tiles[x][0] = Tile(TileType.WALL, random.choice([34, 35]), x, 0)
            self.tiles[3][0] = Tile(TileType.WALL, 22, 3, 0)  # Special Tile for eye candy
            # Build upper wall tiles
            self.tiles[0][1] = Tile(TileType.WALL, 49, 0, 0)
            self.tiles[-1][1] = Tile(TileType.WALL, 52, 0, 0)
            for x in range(1, self.width - 1):
                self.tiles[x][1] = Tile(TileType.WALL, random.choice([16, 17, 18, 38, 50, 51, 115]), x, 1)
            # Build left and right wall tiles
            x = 0
            for y in range(2, self.height - 1):
                self.tiles[0][y] = Tile(TileType.WALL, 49, 0, y)
                self.tiles[-1][y] = Tile(TileType.WALL, 52, -1, y)
            # Build bottom wall tiles
            self.tiles[0][-1] = Tile(TileType.WALL, 81, 0, 0)
            self.tiles[-1][-1] = Tile(TileType.WALL, 84, 0, 0)
            for x in range(1, self.width - 1):
                self.tiles[x][-1] = Tile(TileType.WALL, 82, x, -1)
            self.tiles[11][-1] = Tile(TileType.WALL, 6, 11, -1)  # eye candy tile

            # Build center area with paths and pillars
            for y in range(2, self.height - 1):
                for x in range(1, self.width - 1):
                    if y % 2 != 0 and x % 2 != 1:
                        self.tiles[x][y] = Tile(TileType.WALL, random.choice([97, 113]), x, y)
                    else:
                        self.tiles[x][y] = Tile(TileType.EMPTY, random.choice(
                            [1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 19, 19,
                             19, 20]), x, y)
            # Place some boxes
            box_locations = [(2,6), (8,1),(8,2),(8,3),(8,4),(8,5),(8,6),(8,8),(8,9),(8,10),(8,11),(8,12),(8,13),
                             (2,7),(3,7),(4,7),(5,7),(6,7),(7,7),(9,7),(10,7),(11,7),(12,7),(13,7),(14,7)]
            for y,x in box_locations:
                self.place_box(x,y)

            # Place spike traps
            self.spike_traps.append(SpikeTrap(4, 2, 600, 900, active_ticks=90, armed=True))
            self.spike_traps.append(SpikeTrap(10, 2, 600, 1000, active_ticks=90, armed=True))
            self.spike_traps.append(SpikeTrap(10, 14, 600, 1000, active_ticks=90, armed=True))
            self.spike_traps.append(SpikeTrap(4, 14, 600, 900, active_ticks=90, armed=True))
            self.spike_traps.append(SpikeTrap(1, 5, 600, 1000, active_ticks=90, armed=True))
            self.spike_traps.append(SpikeTrap(1, 11, 600, 900, active_ticks=90, armed=True))
            self.spike_traps.append(SpikeTrap(13, 11, 600, 1000, active_ticks=90, armed=True))
            self.spike_traps.append(SpikeTrap(13, 5, 600, 900, active_ticks=90, armed=True))

            self.spike_traps.append(SpikeTrap(5, 6, 500, 800, active_ticks=90, armed=True))
            self.spike_traps.append(SpikeTrap(5, 10, 500, 800, active_ticks=90, armed=True))
            self.spike_traps.append(SpikeTrap(9, 6, 500, 800, active_ticks=90, armed=True))
            self.spike_traps.append(SpikeTrap(9, 10, 500, 800, active_ticks=90, armed=True))

            # Place power up
            p_up = PowerUp(7,8,PowerUpType.BOMB_PLUS)
            self.tiles[7][8].set_content(p_up)
            self.register_event(GameEvent(EventType.SPAWN_POWER_UP, {"x": p_up.x, "y":p_up.y,"t":p_up.get_power_up_type().value}))

            p_up = PowerUp(10,4,PowerUpType.POWER_PLUS)
            self.tiles[10][4].set_content(p_up)
            self.register_event(GameEvent(EventType.SPAWN_POWER_UP, {"x": p_up.x, "y":p_up.y,"t":p_up.get_power_up_type().value}))

            p_up = PowerUp(4,12,PowerUpType.POWER_PLUS)
            self.tiles[4][12].set_content(p_up)
            self.register_event(GameEvent(EventType.SPAWN_POWER_UP, {"x": p_up.x, "y":p_up.y,"t":p_up.get_power_up_type().value}))

            # Define player starting positions
            self.starts = [(1, 2), (13, 14)]
        else:
            self.load_from_file(file)

    def register_event(self, event):
        """ :param event: GameEvent instance """
        for i in range(len(self.events)):
            self.events[i].append(event)

    def create_player(self):
        id = len(self.players)
        player = Player(*self.starts[id])
        self.players.append(player)
        return id, player

    @staticmethod
    def distance_squared(p1, p2):
        return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2

    def player_action(self, id, action):
        p = self.players[id]

        ### Powerup Collection ###
        # Is before the action to happen also on a 'wait' action if the P-Up spawned below the player last tick # TODO maybe make powerups be non-collectable for a seconds upon spawning so that the client can even SEE such spawns?
        player_tile_x, player_tile_y = (floor(p.x), floor(p.y))
        current_player_tile = self.tiles[player_tile_x][player_tile_y]

        if current_player_tile.has_content():
            if current_player_tile.get_content().is_of_type(EntityType.POWER_UP):
                self.apply_power_up(p, id, current_player_tile.get_content())
                current_player_tile.set_content(None)
                self.register_event(GameEvent(EventType.REMOVE_POWER_UP, {"x": player_tile_x, "y": player_tile_y}))

        # invert player input upon affliction
        if p.is_inverted() and action in ["up","down","left","right"]:
            action = p.invert_action(action)


        if action == "wait":
            if not p.is_autowalking(): ## TODO this is redundantly in every actions block, maybe we can refactor somehow?
                return
            else:
                action = p.last_action

        if action == "slime":
            if not p.has_slime_cooldown():
                self.slime_player(int(not id))
            if not p.is_autowalking():
                return
            else:
                action = p.last_action

        if action == "taunt":
            self.player_taunt(id)
            if not p.is_autowalking():
                return
            else:
                action = p.last_action

        if action == "bomb":
            self.place_bomb(id)
            if not p.is_autowalking():
                return
            else:
                action = p.last_action

        # ELSE "up" "down" "left" "right"

        # Move action
        # if p.automove:
        #     action = p.last_action
        dir = DIR[action]
        x_dir, y_dir = dir
        nx, ny = p.x + (p.speed * x_dir), p.y + (p.speed * y_dir)
        slide = None
        collision = False

        # 3 Tiles to check: Tile in direction, and left and right of that (viewed in direction of movement)
        #       □  upper
        # --> o □  front
        #       □  lower

        front_tile = self.tiles[player_tile_x + x_dir][player_tile_y + y_dir]
        left_offset_x, left_offset_y = TILE_OFFSETS[(x_dir, y_dir)][0]
        left_tile = self.tiles[player_tile_x + left_offset_x][player_tile_y + left_offset_y]
        right_offset_x, right_offset_y = TILE_OFFSETS[(x_dir, y_dir)][1]
        right_tile = self.tiles[player_tile_x + right_offset_x][player_tile_y + right_offset_y]

        if not front_tile.is_passable():
            collision_point_x, collision_point_y = (nx + PLAYER_RADIUS * x_dir, ny + PLAYER_RADIUS * y_dir)
            tile_at_col_point = self.tiles[floor(collision_point_x)][floor(collision_point_y)]
            if tile_at_col_point == front_tile:
                # Collision with frontal wall OR slide along it depending on position.
                # Compare distance of the player to the center of the tile he is standing on
                # by getting the vector of the tile center to the player position.
                # the vector then denotes the slide direction too.
                #           v-- player pos
                #    ┌───────┐
                #    │      T│ <- slide left
                #    │      F│ <- no slide
                #    │   x  F│ <- no slide
                #    │      F│ <- no slide
                #    │      T│ <- slide right
                #    └───────┘
                tile_center_x, tile_center_y = player_tile_x + 0.5, player_tile_y + 0.5
                player_vector = pygame.math.Vector2((p.x - tile_center_x, p.y - tile_center_y))

                if player_vector.length_squared() > FRONTAL_SLIDE_THRESHOLD:
                    # slide, player is at edge. First, get the direction to slide to:
                    front_tile_center_x, front_tile_center_y = front_tile.get_center()
                    forward_vector = pygame.math.Vector2(
                        (front_tile_center_x - tile_center_x, front_tile_center_y - tile_center_y))
                    slide_left = -player_vector.x * forward_vector.y + player_vector.y * forward_vector.x < 0
                    if slide_left:
                        left_offset_x, left_offset_y = TILE_OFFSETS[(x_dir, y_dir)][2]
                        left_side_wall_tile = self.tiles[player_tile_x + left_offset_x][player_tile_y + left_offset_y]
                        if left_side_wall_tile.is_passable() and left_tile.is_passable():
                            slide = "left"
                        else:
                            collision = True
                    else:
                        right_offset_x, right_offset_y = TILE_OFFSETS[(x_dir, y_dir)][3]
                        right_side_wall_tile = self.tiles[player_tile_x + right_offset_x][
                            player_tile_y + right_offset_y]
                        if right_side_wall_tile.is_passable() and right_tile.is_passable():
                            slide = "right"
                        else:
                            collision = True
                else:
                    collision = True

        # Get nearer neighboring tile (left or right neighbour)
        elif self.distance_squared((nx, ny), (right_tile.x + 0.5, right_tile.y + 0.5)) < self.distance_squared((nx, ny),
                                                                                                               (
                                                                                                                       left_tile.x + 0.5,
                                                                                                                       left_tile.y + 0.5)):  # closer to the right neighboring tile. compare to that.
            if not right_tile.is_passable():

                wall_corner_x, wall_corner_y = (
                    right_tile.x + RIGHT_CORNER_OFFSETS[dir][0], right_tile.y + RIGHT_CORNER_OFFSETS[dir][1])

                # If corner would be inside player collision radius: Collision.
                # player distance to that point < player radius ?
                if self.distance_squared((wall_corner_x, wall_corner_y), (nx, ny)) < PLAYER_RADIUS ** 2:
                    slide = "left"


        else:  # player in left half of the tile, check against left neighboring tile's closest corner
            if not left_tile.is_passable():

                wall_corner_x, wall_corner_y = (
                    left_tile.x + LEFT_CORNER_OFFSETS[dir][0], left_tile.y + LEFT_CORNER_OFFSETS[dir][1])

                # If corner would be inside player collision circle: Collision.
                # Distance < player radius ?
                if self.distance_squared((wall_corner_x, wall_corner_y), (nx, ny)) < PLAYER_RADIUS ** 2:
                    slide = "right"

        ### ELSE: we move.

        if slide:
            slide_factors = SLIDE_FACTORS[dir][slide]
            p.move(p.speed * 0.5 * slide_factors[0], p.speed * 0.5 * slide_factors[1], action=action)
        elif collision:
            p.move(0, 0, action=action)  # Turns the player only
        else:
            p.move(p.speed * x_dir, p.speed * y_dir, action=action)

        self.register_event(GameEvent(EventType.PLAYER_MOVED, {"id": id,
                                                               "x": round(p.x, 2),
                                                               "y": round(p.y, 2),
                                                               "f": p.facing}))

    def place_box(self, x: int, y: int):
        if not self.tiles[x][y].has_content():
            box = Box(x,y)
            self.tiles[x][y].set_content(box)
            self.register_event(GameEvent(EventType.SPAWN_BOX, {"x": x, "y": y}))

    def place_bomb(self, id: int):
        player = self.players[id]
        x, y = (floor(p) for p in player.get_pos())
        tile = self.tiles[x][y]

        if tile.has_content() or player.bombs <= 0:
            return
        else:
            player.bombs -= 1
            self.register_event(GameEvent(EventType.PLAYER_CHANGE_BOMBS_COUNT, {"id": id, "b": player.bombs}))
        bomb = Bomb(x,y,player.power,id,TIME_TILL_EXPLOSION)
        self.bombs.append(bomb) # TODO needed or make Entity[] ?
        tile.set_content(bomb)
        self.register_event(GameEvent(EventType.SPAWN_BOMB, {"x": x, "y": y, "t": TIME_TILL_EXPLOSION}))

    def update(self, id: int):
        """ :param id: player ID calling this function. The Game will only update for player ID 0 """
        if id != 1:  # TODO workaround. without this, both clients call this method, resulting in 2x game speed
            return

        # update anger display
        for id in range(len(self.players)):
            anger_history = self.anger_histories[id]
            for i in range(1,len(anger_history)):
                anger_history[i-1] = anger_history[i] - (ANGER_HISTORY_DECAY_FACTOR * anger_history[i])
            current_raw_anger = self.raw_angers[id]
            if (current_raw_anger >= self.anger_retention_container[id][1]) or (current_raw_anger > 0 and self.anger_retention_container[id][0] == 0):
                self.anger_retention_container[id] = [ANGER_INPUT_RETENTION_TICKS, current_raw_anger]
            if self.anger_retention_container[id][0] > 0:
                self.anger_retention_container[id][0] -= 1
                if self.anger_retention_container[id][1] > current_raw_anger:
                    current_raw_anger = self.anger_retention_container[id][1]
            anger_history[-1] = current_raw_anger
            self.aggregated_angers[id] = sum(anger_history) / self.anger_history_max

        self.register_event(GameEvent(EventType.ANGER_INFO, {"0":self.aggregated_angers[0],"1":self.aggregated_angers[1]}))

        # Update Crushing Boxes
        i = 0
        while i < len(self.crushing_boxes):
            crushing_box = self.crushing_boxes[i]
            crushing_box.tick()
            x,y = crushing_box.get_pos()
            for id, player in enumerate(self.players):
                px, py = player.get_tile_pos()
                if px == int(x) and py == int(y) and player.is_immortal() == False:
                    player.lifes -= 1
                    player.set_immortal_time(200)
                    self.register_event(GameEvent(EventType.PLAYER_DAMAGED, {"id": id, "dmg": 1}))
                    # TODO push player aside upon crush? without, he can freely walk inside the falling box until he leaves the tile. but that can be as desired too.
            if crushing_box.timer_expired():
                tile = self.tiles[int(x)][int(y)]
                tile.set_content(Box(x,y))
                del self.crushing_boxes[i]
                self.register_event(GameEvent(EventType.SPAWN_BOX, {"x": x, "y": y}))
                self.register_event(GameEvent(EventType.REMOVE_CRUSHING_BOX, {"x":x,"y":y}))
            else:
                i += 1

        # Update Falling Boxes
        i = 0
        while i < len(self.falling_boxes):
            falling_box = self.falling_boxes[i]
            falling_box.tick()
            if falling_box.timer_expired():
                x,y = falling_box.get_pos()
                tile = self.tiles[int(x)][int(y)]
                crushing_box = CrushingBox(x,y,CRUSHING_BOX_DURATION)
                tile.set_content(crushing_box)
                self.crushing_boxes.append(crushing_box)
                del self.falling_boxes[i]
                self.register_event(GameEvent(EventType.REMOVE_FALLING_BOX, {"x":x,"y":y}))
                self.register_event(GameEvent(EventType.SPAWN_CRUSHING_BOX, {"x":x,"y":y,"t":crushing_box.ticks_to_expiration}))
            else:
                i += 1

        # Spawn new falling boxes
        box = self.falling_box_scheduler.tick(self)
        if box:
            self.register_event(GameEvent(EventType.SPAWN_FALLING_BOX, {"x":box.x,"y":box.y,"t":box.ticks_to_expiration}))

        # handle bombs
        i = 0
        while i < len(self.bombs):
            bomb = self.bombs[i]
            bomb.tick()
            exploded = False
            if bomb.timer_expired():
                exploded = True
            for explosion in self.explosions:
                if bomb.x == explosion.x and bomb.y == explosion.y:
                    exploded = True
                    break
            if exploded:
                player = self.players[bomb.get_owner_id()]
                player.bombs += 1
                self.register_event(GameEvent(EventType.PLAYER_CHANGE_BOMBS_COUNT, {"id": id, "b": player.bombs}))
                bx, by = bomb.get_pos()
                self.explode(bomb)
                self.tiles[int(bx)][int(by)].set_content(None)
                del self.bombs[i]
                self.register_event(GameEvent(EventType.REMOVE_BOMB, {"x": bx, "y": by}))
                ## TODO code structuring / levels of event creation
                continue
            else:
                i += 1


        # handle spike traps
        for trap in self.spike_traps:
            trap.tick(self)
            if trap.should_activate():
                # spring the trap!
                trap.activate()
                self.register_event(GameEvent(EventType.ACTIVATE_TRAP, {"x": trap.x, "y": trap.y}))
                trap.handle_damage(self.players, self)
            elif trap.is_active():
                trap.handle_damage(self.players, self)


        # handle explosions
        i = 0
        while i < len(self.explosions):
            explosion = self.explosions[i]
            explosion.tick()
            ex, ey = explosion.get_pos()
            # check if player is here
            for id, player in enumerate(self.players):
                if not player.is_immortal():
                    # print(floor(player.x - 0.5), floor(player.y - 0.5))
                    if floor(player.x) == ex and floor(player.y) == ey:
                        player.lifes -= 1
                        player.set_immortal_time(200)
                        self.register_event(GameEvent(EventType.PLAYER_DAMAGED, {"id": id, "dmg": 1}))

            if explosion.timer_expired():
                self.register_event(GameEvent(EventType.REMOVE_EXPLOSION, {"x": ex, "y": ey}))
                del self.explosions[i]
            else:
                i += 1

        # handle players
        for i, player in enumerate(self.players):

            player.speed = player.base_speed + (self.aggregated_angers[not i] * player.max_bonus_speed)

            if player.immortal_ticks > 0:
                player.immortal_ticks -= 1
            if player.immortal_ticks == 0:
                self.register_event(GameEvent(EventType.PLAYER_MORTAL, {"id": i}))
                player.immortal_ticks -= 1

            if player.is_inverted():
                player.inverted_ticks -= 1
                if player.inverted_ticks <= 0:
                    self.register_event(GameEvent(EventType.PLAYER_INVERT_KEYBOARD_OFF, {"id": id}))

            if player.is_autowalking():
                player.autowalk_ticks -= 1
                if player.autowalk_ticks <= 0:
                    self.register_event(GameEvent(EventType.PLAYER_AUTOWALK_OFF, {"id": id}))

            if player.slime > 0:
                player.slime -= 1
            if player.slime == 0:
                self.register_event(GameEvent(EventType.PLAYER_NOT_SLIMEY, {"id": i}))
                player.slime -= 1

            if player.has_slime_cooldown():
                player.slime_cooldown_ticks -= 1

            if player.lifes <= 0:
                self.winner = int(not (i))
                self.register_event(GameEvent(EventType.WINNER, {"id": self.winner}))

    def explode(self, bomb: Bomb):
        power = bomb.get_power()
        origin_x, origin_y = bomb.get_pos()
        explosion = Explosion(origin_x, origin_y, EXPLOSION_DURATION)
        self.explosions.append(explosion)
        for dir in DIR.values():
            for i in range(power):
                current_x = int(origin_x + dir[0] * i)
                current_y = int(origin_y + dir[1] * i)
                tile = self.tiles[current_x][current_y]
                if tile.type == TileType.EMPTY or (tile.has_content() and tile.get_content().is_of_type(EntityType.BOX)):
                    explosion = Explosion(current_x, current_y, EXPLOSION_DURATION)
                    self.explosions.append(explosion)
                    self.register_event(GameEvent(EventType.SPAWN_EXPLOSION, {"x": current_x, "y": current_y}))

                    # Destroy Boxes
                    if tile.has_content() and tile.get_content().is_of_type(EntityType.BOX):
                        tile.set_content(None)
                        self.register_event(GameEvent(EventType.REMOVE_BOX, {"x": current_x, "y": current_y}))
                        # On an empty Tile: Attempt to spawn a power-Up:
                        if tile.type == TileType.EMPTY:
                            power_up = self.power_up_scheduler.tick(current_x, current_y, self)
                            if power_up:
                                self.register_event(GameEvent(EventType.SPAWN_POWER_UP, {"x": power_up.x, "y":power_up.y,"t":power_up.get_power_up_type().value}))
                        break
                else:
                    break

    def load_from_file(self, filename):
        f = open(filename, 'r')
        field = json.load(f)
        f.close()

        tiles = field['tiles']
        self.height = len(tiles)
        self.width = len(tiles[0])

        self.tiles = [[Tile(TileType(tile['type']), tile['sprite'], x, y) for y, tile in enumerate(row)]
                      for x, row
                      in enumerate(tiles)]

        # place objects (such as boxes) on
        objects = field['objects']
        for obj in objects:
            if obj['type'] == 'box':
                self.place_box(obj['x'], obj['y'])

        # place player starting positions
        starts = field['starts']
        self.starts = [(start['x'], start['y']) for start in starts]

    def write_field_to_file(self):
        """
        This function is only used for serialising the current field into a json file.
        It's not necessary, if you already have a file with a serialised field.
        """
        f = open('field.json', 'w')
        f.write(json.dumps({
            'tiles': [[{
                'type': tile.type.value,
                'sprite': tile.sprite_id
            } for tile in row] for row in self.tiles],
            'objects': [{
                'type': 'box',
                'x': box.x,
                'y': box.y
            } for box in map(lambda t: t.get_content(), filter(lambda t: t.has_content() and t.get_content.is_of_type(EntityType.BOX), self.tiles))],
            'starts': [{
                'x': position[0],
                'y': position[1]
            } for position in self.starts]
        }))
        f.close()

    def apply_power_up(self, player:Player, id:int, power_up:PowerUp):
        if power_up.get_power_up_type() == PowerUpType.INVERT_KEYBOARD:
            player.set_invertion_time(INVERTED_KEYBOARD_TICKS)
            self.register_event(GameEvent(EventType.PLAYER_INVERT_KEYBOARD_ON, {"id": id}))

        elif power_up.get_power_up_type() == PowerUpType.AUTOWALK:
            player.set_autowalk_time(AUTOWALK_TICKS)
            self.register_event(GameEvent(EventType.PLAYER_AUTOWALK_ON, {"id": id}))

        elif power_up.get_power_up_type() == PowerUpType.POWER_PLUS:
            player.power += 1
            self.register_event(GameEvent(EventType.PLAYER_CHANGE_POWER_AMOUNT, {"id": id, "p": player.power}))

        elif power_up.get_power_up_type() == PowerUpType.BOMB_PLUS:
            player.bombs += 1
            self.register_event(GameEvent(EventType.PLAYER_CHANGE_BOMBS_COUNT, {"id": id, "b": player.bombs}))


    def player_taunt(self, id: int):
        """ :param id: Taunting player ID """
        self.register_event(GameEvent(EventType.PLAYER_TAUNT, {"id": id, "t":TAUNT_DURATION}))
        # TODO here we could add cooldowns or different kinds of taunts

    def slime_player(self, id: int):
        self.players[id].slime = 500
        self.players[not id].slime_cooldown_ticks = SLIME_COOLDOWN
        self.register_event(GameEvent(EventType.PLAYER_SLIMED, {"id": id}))

    def precompute_anger_history_max(self):
        temp_history = [1.0 for _ in range(ANGER_HISTORY_LEN)]
        for _ in range(ANGER_HISTORY_LEN):
            for i in range(1, ANGER_HISTORY_LEN):
                temp_history[i-1] = temp_history[i] - (temp_history[i] * ANGER_HISTORY_DECAY_FACTOR)
                temp_history[-1] = 1.0
        return sum(temp_history)
