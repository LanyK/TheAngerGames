import pygame
from math import floor
import numpy as np
from typing import List, Tuple
from Player import PlayerHistory
from DrawMethods import BarDrawer, TextDrawer, color_change
from Sprites import Spritesheet, Charsheet, Animation


CRUSHING_BOX_SPAWN_TICKS = 20
CRUSHING_BOX_SPAWN_HEIGHT = CRUSHING_BOX_SPAWN_TICKS * 2

FALLING_BOX_SPAWN_TICKS = 60*3 # TODO this is a magic value that should match the one in Schedulers.py
FALLING_BOX_SPAWN_HEIGHT = FALLING_BOX_SPAWN_TICKS * 2 + CRUSHING_BOX_SPAWN_HEIGHT#360
FALLING_BOX_CRUSH_HEIGHT = CRUSHING_BOX_SPAWN_HEIGHT # despawn at this hight




def alpha_sprite(surface, alpha: int):
    surface = surface.copy()
    arr = pygame.surfarray.pixels_alpha(surface)
    is_visible = arr[:, :] > 0
    arr[:, :][is_visible] = alpha
    return surface


class View:
    def __init__(self, game_width_px: int, game_height_px: int, name="None"):
        """"
        :param width: width of the View Windox in Pixels
        :param height: height of the View Windom in Porxels
        :param name: Name of the  Window
        """
        self.game_width = game_width_px
        self.display_width = game_width_px
        self.game_height = game_height_px
        self.display_height = game_height_px + 60 # gui area
        self.screen = pygame.display.set_mode((self.display_width, self.display_height), pygame.SRCALPHA)
        self.screen.fill((44,35,51))
        self.gridsize = 32  # size of one tile in pixel
        self.slimy = False

        self.empty_image = pygame.image.load("res/empty.png")
        self.empty_image.convert()

        #self.shadow_image = pygame.image.load("res/TODO")
        self.shadow_image = pygame.Surface((32,32))
        self.shadow_image.convert_alpha()
        self.shadow_image.set_alpha(60)
        self.shadow_image.fill((0,0,0))

        self.wall_image = pygame.image.load("res/wall.png")
        self.wall_image.convert()
        self.wall_front_image = pygame.image.load("res/wall_front.png")
        self.wall_front_image.convert()

        self.box_image = pygame.image.load("res/box.png")
        self.box_image.convert()
        self.box_front_image = pygame.image.load("res/box_front.png")
        self.box_front_image.convert()

        self.bomb_image = pygame.image.load("res/bomb.png")
        self.bomb_image.convert_alpha()

        self.explosion_image = pygame.image.load("res/explosion.png")
        self.explosion_image.convert()

        self.slime_image = pygame.image.load("res/slime_draft.png")
        self.slime_image.convert()

        self.speech_bubble_looser = pygame.image.load("res/speech_bubble_looser.png")
        self.speech_bubble_looser.convert_alpha()

        ### GUI ###

        self.heart_img = pygame.image.load("res/heart.png")
        self.heart_img.convert_alpha()

        self.bombs_img = pygame.image.load("res/bombs.png")
        self.bombs_img.convert_alpha()

        self.power_img = pygame.image.load("res/atomic.png")
        self.power_img.convert_alpha()

        self.anger_meter_img = pygame.image.load("res/anger_meter.png")
        self.anger_meter_img.convert_alpha()

        # Inverted Keyboard anims
        self.player_confused_fg_spritesheet = Spritesheet.from_file("res/confused_anim_fg.png", sprite_size=(32,32))
        self.player_confused_bg_spritesheet = Spritesheet.from_file("res/confused_anim_bg.png", sprite_size=(32,32))
        self.player_confused_fg_anims = [Animation(self.player_confused_fg_spritesheet, {0:7,1:7}) for _ in range(2)]
        self.player_confused_bg_anims = [Animation(self.player_confused_bg_spritesheet, {0:7,1:7}) for _ in range(2)]

        # Autowalk anims
        self.player_autowalk_fg_spritesheet = Spritesheet.from_file("res/autowalk_anim_fg.png", sprite_size=(32,32))
        self.player_autowalk_bg_spritesheet = Spritesheet.from_file("res/autowalk_anim_bg.png", sprite_size=(32,32))
        self.player_autowalk_fg_anims = [Animation(self.player_autowalk_fg_spritesheet, {0:5,1:5}) for _ in range(2)]
        self.player_autowalk_bg_anims = [Animation(self.player_autowalk_bg_spritesheet, {0:5,1:5}) for _ in range(2)]

        self.power_up_spritesheet = Spritesheet.from_file("res/power_ups.png", sprite_size=(32,32))

        self.power_up_animations: list = [None for _ in range(len(self.power_up_spritesheet))]

        arrow_power_up_anim = Animation(Spritesheet.from_file("res/power_up_arrow.png", sprite_size=(32,32)),{0:12,1:12,2:12,3:12,4:12})
        move_power_up_anim = Animation(Spritesheet.from_file("res/power_up_move.png", sprite_size=(32,32)),{0:8,1:8,2:8,3:8,4:8})
        power_power_up_anim = Animation(Spritesheet.from_file("res/power_up_red.png", sprite_size=(32,32)),{0:12,1:12,2:12,3:12,4:12})
        bomb_power_up_anim = Animation(Spritesheet.from_file("res/power_up_bomb.png", sprite_size=(32,32)),{0:18,1:30,2:30,3:30,4:30,5:6,6:6,7:6,8:6})

        self.power_up_animations[0] = arrow_power_up_anim
        self.power_up_animations[1] = move_power_up_anim
        self.power_up_animations[2] = power_power_up_anim
        self.power_up_animations[3] = bomb_power_up_anim

        self.player_spritesheet = Spritesheet.from_file("res/angerman_4dir.png", sprite_size=(32, 32))
        self.player_transparent_spritesheet = Spritesheet.from_image_list([alpha_sprite(x, 120) for x in self.player_spritesheet.sprites], "trans_player")

        player_walk_right_anim = Animation(Spritesheet.from_file(
            "res/angerman_walk_right.png",
            sprite_size=(32, 32)),
            {0: 6, 1: 6})
        player_walk_down_anim = Animation(Spritesheet.from_file(
            "res/angerman_walk_down.png",
            sprite_size=(32, 32)),
            {0: 8, 1: 8})
        player_walk_left_anim = Animation(Spritesheet.from_file(
            "res/angerman_walk_left.png",
            sprite_size=(32, 32)),
            {0: 6, 1: 6})
        player_walk_up_anim = Animation(Spritesheet.from_file(
            "res/angerman_walk_up.png",
            sprite_size=(32, 32)),
            {0: 8, 1: 8})

        # down, right, up, left; corresponds to the facing enum of the game.
        self.player_walking_animations = [player_walk_down_anim,
                                          player_walk_right_anim,
                                          player_walk_up_anim,
                                          player_walk_left_anim]
        self.self_player_history = PlayerHistory()  # used for animation consistency
        self.other_player_history = PlayerHistory()

        self.fire_trap_animation = Animation(Spritesheet.from_file("res/lavapit.png", sprite_size=(32, 32)),
                                             {0: 5, 1: 20, 2: 25, 3: 30})  ## TODO this is a placeholder

        # Bombs will shallow copy the animation data and overwrite the timing dict for the specific bomb countdown
        self.bomb_sprite_sheet = Spritesheet.from_file("res/bomb_anim.png", sprite_size=(32, 32))
        self.bomb_animations: dict = dict()  # (x,y) -> Animation

        self.tileset = Spritesheet.from_file("res/Tileset2.png", sprite_size=(32, 32))
        self.charsheet = Charsheet(Spritesheet.from_file("res/charset.png", sprite_size=(14, 14)))
        self.charsheet.load_spacing_map("res/charset_offsets.json")

        self.box_image, _ = self.tileset.get_sprite(101)
        self.box_front_image, _ = self.tileset.get_sprite(101 - 16)

        pygame.display.set_caption(name)

    def update(self):
        pygame.display.update()

    def get_canvas(self):
        return self.screen

    def draw_game_over_screen(self, players, id, msg, color):
        self.screen.fill((0, 0, 0))
        TextDrawer.draw(self.charsheet, self.screen, (8, 2), msg, horizontal_spacing=-1, color=color)
        self.draw_players(players, id)
        self.update()

    def draw_init_screen(self, msg, color):
        # todo: make it look nicer
        self.screen.fill((0, 0, 0))
        TextDrawer.draw(self.charsheet, self.screen, (8, 2), msg, horizontal_spacing=-1, color=color)
        self.update()

    def draw_game(self, field, boxes, inactive_traps, active_traps, power_ups, bombs, explosions, falling_boxes, crushing_boxes, players, active_taunts, id, clock):
        self.draw_background(field)
        self.draw_traps(inactive_traps, active_traps)
        self.draw_power_ups(power_ups)
        self.draw_boxes(boxes)
        self.draw_bombs(bombs)
        self.draw_explosions(explosions)
        self.draw_players(players, id)
        self.draw_foreground(field, boxes, falling_boxes, crushing_boxes, players[id].slimey, players[id])
        self.draw_gui(players, clock, id)
        self.draw_speech_bubbles(players, active_taunts)
        self.update()

    def draw_speech_bubbles(self, players, active_taunts):
        """ Taunts have the form [id,ticks], to be potentially made into [id,ticks,TYPE] in the future as a TODO """
        for id,_ in active_taunts.items():
            player = players[id]
            x,y, = player.get_pos()
            self.screen.blit(self.speech_bubble_looser, ((self.gridsize * x) - 50, (self.gridsize * y) - 90))

    def draw_background(self, field: List[List[Tuple[int, int]]]):
        """
        Everything drawn BEFORE the players

        :param field: the field containing static get_spritestuff (walls, boxes, etc) in the form (type_id,sprite_id)
        """
        self.screen.fill((44, 35, 51))
        for x, column in enumerate(field):
            for y, (type_id, sprite_id) in enumerate(column):
                img, img_size = self.tileset.get_sprite(sprite_id)
                self.screen.blit(img, (self.gridsize * x, self.gridsize * y))

    def draw_gui(self, players, clock, id):

        ### Regular Player Info GUI ###

        # background for player gui TODO use a fancy png

        box_pos = (int(self.game_width * 0.03), self.game_height + 5)
        box_height = 47
        box_width = 256
        BarDrawer.draw(self.screen, box_pos, bar_height=box_height, full_bar_width=box_width, fill_percent=1.0, color=(90, 25, 25))
        BarDrawer.draw(self.screen, (box_pos[0] + 2, box_pos[1] + 2), bar_height=box_height - 4, full_bar_width=box_width - 4, fill_percent=1.0, color=(194,171,153))

        # Sprite on the left
        player_sprite, _ = self.player_spritesheet.get_sprite(0)

        if id:
            player_sprite = color_change(player_sprite)

        self.screen.blit(player_sprite, (int(self.game_width * 0.05), self.game_height + 12))

        # Info beside sprite
        your_lifes = players[id].lifes
        enemy_lifes = players[not id].lifes

        text = str(your_lifes)
        self.screen.blit(self.heart_img, (int(self.game_width * 0.15), self.game_height + 11))
        TextDrawer.draw(self.charsheet, self.screen, (int(self.game_width * 0.23), self.game_height + 22), text, horizontal_spacing=-1, color=(255, 0, 0))

        your_bombs = players[id].bombs
        self.screen.blit(self.bombs_img, (int(self.game_width * 0.27), self.game_height + 10))
        TextDrawer.draw(self.charsheet, self.screen, (int(self.game_width * 0.35), self.game_height + 22), your_bombs, horizontal_spacing=-1, color=(255, 0, 0))

        your_power = players[id].power
        self.screen.blit(self.power_img, (int(self.game_width * 0.39), self.game_height + 10))
        TextDrawer.draw(self.charsheet, self.screen, (int(self.game_width * 0.47), self.game_height + 22), your_power, horizontal_spacing=-1, color=(255, 0, 0))


        ### ENEMY info

        ### background
        box_pos = (int(self.game_width * 0.61), self.game_height + 5)
        box_height = 47
        box_width = 170
        BarDrawer.draw(self.screen, box_pos, bar_height=box_height, full_bar_width=box_width, fill_percent=1.0, color=(90, 25, 25))
        BarDrawer.draw(self.screen, (box_pos[0] + 2, box_pos[1] + 2), bar_height=box_height - 4, full_bar_width=box_width - 4, fill_percent=1.0, color=(194,171,153))

        own_player = players[id]
        other_player = players[not id]

        BarDrawer.draw(self.screen, (int(self.game_width * 0.78), self.game_height + 18), bar_height=21, full_bar_width=76, fill_percent=1, color=(122, 0, 0))
        BarDrawer.draw(self.screen, (int(self.game_width * 0.78), self.game_height + 18), bar_height=21, full_bar_width=76, fill_percent=other_player.anger, color=(255, 0, 0))

        player_sprite, _ = self.player_spritesheet.get_sprite(0)

        if not id:
            player_sprite = color_change(player_sprite)

        self.screen.blit(player_sprite, (int(self.game_width * 0.63), self.game_height + 12))

        self.screen.blit(self.anger_meter_img, (int(self.game_width * 0.66), self.game_height + 12))

        # text = str(enemy_lifes)
        # self.screen.blit(self.heart_img, (int(self.game_width * 0.55), self.game_height + 1))
        # TextDrawer.draw(self.charsheet, self.screen, (int(self.game_width * 0.63), self.game_height + 12), text, horizontal_spacing=-1, color=(255, 0, 0))

        # enemy_bombs = players[not id].bombs
        # self.screen.blit(self.bombs_img, (int(self.game_width * 0.67), self.game_height + 1))
        # TextDrawer.draw(self.charsheet, self.screen, (int(self.game_width * 0.75), self.game_height + 12), enemy_bombs, horizontal_spacing=-1, color=(255, 0, 0))

        # enemy_power = players[not id].power
        # self.screen.blit(self.power_img, (int(self.game_width * 0.79), self.game_height + 1))
        # TextDrawer.draw(self.charsheet, self.screen, (int(self.game_width * 0.87), self.game_height + 12), enemy_power, horizontal_spacing=-1, color=(255, 0, 0))

        ### Debug display ###

        # Self anger
        # BarDrawer.draw(self.screen, (15, 3), bar_height=12, full_bar_width=30, fill_percent=1, color=(122, 0, 0))
        # BarDrawer.draw(self.screen, (15, 3), bar_height=12, full_bar_width=30, fill_percent=own_player.anger, color=(255, 0, 0))

        fps = round(clock.get_fps())
        text = "FPS: " + str(fps)
        TextDrawer.draw(self.charsheet, self.screen, (240, 2), text, horizontal_spacing=-1, color=(255, 0, 0))

        text = "Load:"
        TextDrawer.draw(self.charsheet, self.screen, (335, 2), text, horizontal_spacing=-1, color=(255, 0, 0))

        workload_percent = (clock.get_rawtime() / clock.get_time())
        BarDrawer.draw(self.screen, (400, 3), bar_height=12, full_bar_width=30, fill_percent=1, color=(122, 0, 0))
        BarDrawer.draw(self.screen, (400, 3), bar_height=12, full_bar_width=30, fill_percent=workload_percent, color=(255, 0, 0))


    def draw_foreground(self, field, boxes, falling_boxes, crushing_boxes, slime, player):
        """
        Everything drawn AFTER the players

        :param field: the field containing static stuff (walls, boxes, etc)
        """

        for (x,y),ticks in falling_boxes.items():
            self.screen.blit(self.shadow_image, (self.gridsize * int(x), (self.gridsize * int(y))))

        for (x,y),ticks in crushing_boxes.items():
            y_offset = int((ticks / CRUSHING_BOX_SPAWN_TICKS) * CRUSHING_BOX_SPAWN_HEIGHT)
            self.screen.blit(self.shadow_image, (self.gridsize * int(x), (self.gridsize * int(y))))
            self.screen.blit(self.box_image, (self.gridsize * int(x), (self.gridsize * int(y))- y_offset))

        for box in boxes:
            self.screen.blit(self.box_front_image, (self.gridsize * box[0], self.gridsize * (box[1] - 1)))

        for (x,y),ticks in crushing_boxes.items():
            y_offset = int((ticks / CRUSHING_BOX_SPAWN_TICKS) * CRUSHING_BOX_SPAWN_HEIGHT)
            self.screen.blit(self.box_front_image, (self.gridsize * int(x), (self.gridsize * int(y - 1))- y_offset))

        for (x,y),ticks in falling_boxes.items():
            y_offset = int((ticks / FALLING_BOX_SPAWN_TICKS) * FALLING_BOX_SPAWN_HEIGHT) + FALLING_BOX_CRUSH_HEIGHT
            self.screen.blit(self.box_image, (self.gridsize * int(x), (self.gridsize * int(y))- y_offset))
            self.screen.blit(self.box_front_image, (self.gridsize * int(x), (self.gridsize * int(y - 1))- y_offset))

        if slime:
            self.screen.blit(self.slime_image, (0, 0))
            self.slimy = True
        else:
            if self.slimy:
                self.slime_image = pygame.image.load("res/slime_draft.png")  # TODO copy instead
                self.slime_image.convert()
                self.slimy = False

        if player.bloody > 0:
            player.bloody -= 1
            bloody_image = pygame.Surface((32*15, 32*16))
            bloody_image.convert_alpha()
            bloody_image.set_alpha(player.bloody*3)
            bloody_image.fill((255, 0, 0))
            self.screen.blit(bloody_image, (0, 0))

    def draw_boxes(self, boxes):
        for box in boxes:
            self.screen.blit(self.box_image, (self.gridsize * box[0], self.gridsize * box[1]))

    def draw_explosions(self, explosions):
        for expl in explosions:
            self.screen.blit(self.explosion_image, (self.gridsize * expl[0], self.gridsize * expl[1]))

    def draw_power_ups(self, power_ups):
        for (x,y),type_id in power_ups.items():
            anim = self.power_up_animations[type_id]
            if anim != None:
                self.screen.blit(anim.get_next_frame(), (self.gridsize * x, self.gridsize * y))
            else:
                self.screen.blit(self.power_up_spritesheet.get_sprite(type_id)[0], (self.gridsize * x, self.gridsize * y))

    def draw_bombs(self, bombs):
        for (x, y), ticks in bombs.items():
            anim = self.bomb_animations.get((x, y), None)
            if not anim:
                anim_len = len(self.bomb_sprite_sheet)
                anim = Animation(self.bomb_sprite_sheet, {i: (ticks // anim_len) + 1 for i in range(anim_len)})
                self.bomb_animations[(x, y)] = anim
            frame = anim.get_next_frame()
            self.screen.blit(frame, (self.gridsize * x, self.gridsize * y))
        # Delete anims of removed bombs
        tmp = []
        for key in self.bomb_animations:
            if key not in bombs:
                tmp.append(key)
        for key in tmp:
            del self.bomb_animations[key]

    def draw_traps(self, inactive_traps: dict, active_traps: set):
        # Frames 0, 1, 2: windup
        # Frame  3:       active
        for (x, y), (max_ticks, remaining_ticks) in inactive_traps.items():
            progress = 1.0 - (remaining_ticks / max_ticks)
            if progress > 0.85:
                frame = 2
            elif progress > 0.60:
                frame = 1
            else:
                frame = 0
            self.screen.blit(self.fire_trap_animation.frames[frame],
                             (self.gridsize * floor(x), self.gridsize * floor(y)))
        for x,y in active_traps:
            self.screen.blit(self.fire_trap_animation.frames[3],
                             (self.gridsize * floor(x), self.gridsize * floor(y)))

    def draw_players(self, players: list, my_id: int):
        """
        :param players: list of Player objects
        :param my_id: id of the player's player object
        """
        own = players[my_id]
        other = players[not my_id]

        players = [own, other, my_id] if own.y < other.y else [other, own, not my_id]
        self.__draw_player(players[0].x, players[0].y, players[0].facing, players[0].immortal, players[0].inverted_keyboard, players[0].autowalk, self.self_player_history, players[2])
        self.__draw_player(players[1].x, players[1].y, players[1].facing, players[1].immortal, players[1].inverted_keyboard, players[1].autowalk, self.other_player_history, not players[2])

    def __draw_player(self, x, y, facing, immortal, inverted_keyboard:bool, autowalk:bool, player_history, pl_id):
        """ :param player_history: the history object of this player, used for animation consistency.
        """
                # 3 Layers per player:
                #    background Effect animations
                #    player sprite
                #    foreground Effect animations

        ### BACKGROUND EFFECT(S) ###
        if inverted_keyboard:
            frame = self.player_confused_bg_anims[pl_id].get_next_frame()
            self.screen.blit(frame, (self.gridsize * (x - 0.5), self.gridsize * (y - 0.90)))

        if autowalk:
            frame = self.player_autowalk_bg_anims[pl_id].get_next_frame()
            self.screen.blit(frame, (self.gridsize * (x - 0.5), self.gridsize * (y - 0.80)))

        ### PLAYER SPRITE ###
        if immortal:  # TODO would be more universally usable if it would just make any given sprite transparent on the spot to have all player animations transparableable. yes thats a word.
            sprite, size = self.player_transparent_spritesheet.get_sprite(facing)
        else:
            if player_history.stands_still(x, y):
                # position did not chance. facing could have changed. display standing aniation in current facing.
                sprite, size = self.player_spritesheet.get_sprite(facing)
                player_history.update(x, y, facing, stood_still=True)
            else:
                # player moved. play movement animation corresponding to facing.

                anim = self.player_walking_animations[facing]
                if player_history.stood_still or player_history.last_facing != facing:  # player stood still or turned, restart from the beginning of the animation.
                    anim.reset_animation()
                sprite = anim.get_next_frame()
                player_history.update(x, y, facing, stood_still=False)
        if pl_id:
            sprite = color_change(sprite)
        self.screen.blit(sprite, (
            self.gridsize * (x - 0.5), self.gridsize * (y - 0.75)))  ## TODO fine tune with collision radius maybe

        ### FOREGROUND EFFECT(S) ###
        if inverted_keyboard:
            frame = self.player_confused_fg_anims[pl_id].get_next_frame()
            self.screen.blit(frame, (self.gridsize * (x - 0.5), self.gridsize * (y - 0.90)))

        if autowalk:
            frame = self.player_autowalk_fg_anims[pl_id].get_next_frame()
            self.screen.blit(frame, (self.gridsize * (x - 0.5), self.gridsize * (y - 0.80)))



    def remove_slime(self, x, y):
        ys = np.arange(0, 512)
        xs = np.arange(0, 480)
        arr = pygame.surfarray.pixels_alpha(self.slime_image)
        mask = (xs[np.newaxis, :] - y) ** 2 + (ys[:, np.newaxis] - x) ** 2 < 23 ** 2
        arr[arr < 40] = 40
        arr[mask] -= 40
        arr[arr < 41] = 0
        pass
