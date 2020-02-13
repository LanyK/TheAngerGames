#!/usr/bin/env python3

import Game
from typing import Union, Dict
from Entities import FallingBox, PowerUpType, PowerUp
from Tiles import TileType
import random

FALLING_BOX_DURATION_UNTIL_CRUSH = 60 * 3

class PowerUpScheduler():

    def __init__(self, spawn_rate=0.1, allow_spawn_on_player=True, grace_period_ticks=60, relative_spawn_rates:Dict[PowerUpType,float]=None):
        """ :param spawn_rate: The rate at which spawn attempts are made
            :param grace_period_ticks: The 'cooldown' when no attempt is made
            :param relative_spawn_rates: The spawn rates to determine the type of spawn WHEN a spawn happens. This will be normalized to a probability distribution. Defaults to 1 for keys if partially given.
        """
        self.spawn_rate = spawn_rate
        self.grace_period_ticks = grace_period_ticks
        self.grace_counter = 0
        self.power_up_probs = self.normalize_probs(relative_spawn_rates)

    def normalize_probs(self,relative_spawn_rates):
        """ Returns a list P, where P[power_up_type.value] = normalized p of that type """
        num_power_up_types = len(PowerUpType)

        # no dict given, or empty. Even probability distribution.
        if relative_spawn_rates == None or len(relative_spawn_rates) == 0:
            return [1/num_power_up_types for _ in range(num_power_up_types)]

        # Compute distr.
        total_prob_mass = sum(relative_spawn_rates.get(type,1.0) for type in PowerUpType)
        return [relative_spawn_rates.get(type,1.0) / total_prob_mass for type in PowerUpType]

    def tick(self, x:int, y:int, game):
        """ Activates the scheduler, that may then spawn a power up to the game at
            the given tile location.
            This scheduler will always begin a grace period of self.grace_period_ticks
            after each spawn,
            and spawn something with a probability of self.spawn_rate if not graceful.
            :param x: x Tile coordinate to spawn at
            :param y: y Tile coordinate to spawn at
            :returns: None or a new FallingBox object at a random location
        """
        if self.grace_counter > 0:
            self.grace_counter -= 1
            return None

        if random.random() >= self.spawn_rate:
            return None
        else:
            # choose power up tipe with relative probabilities
            random_float = random.random()
            i = 0
            consumed_prob = self.power_up_probs[0]
            while i < len(self.power_up_probs) and random_float > consumed_prob:
                i += 1
                consumed_prob += self.power_up_probs[i]

            # there is a small chance that the python float inaccuracy will result in i being one to big.
            # this can happen when random_float ~= 1.0 and sum(self.power_up_probs) < random_float.
            # The sum >should< always be 1.0 - but hey, its floats.
            if i == len(self.power_up_probs):
                i -= 1

            chosen_type = PowerUpType(min(i,len(self.power_up_probs)-1))
            powerUp = PowerUp(x,y,chosen_type)
            tile = game.tiles[x][y]
            tile.set_content(powerUp)
            return powerUp

class FallingBoxScheduler():

    def __init__(self, spawn_rate=0.1, allow_spawn_on_player=True, grace_period_ticks=60):
        self.spawn_rate = spawn_rate
        self.allow_spawn_on_player = allow_spawn_on_player
        self.grace_period_ticks = grace_period_ticks
        self.grace_counter = 0

    def tick(self, game) -> Union[None,FallingBox]:
        """ Activates the scheduler, that may then spawn a falling box to the game.
            It will always begin a grace period of self.grace_period_ticks after each spawn,
            and spawn something with a probability of self.spawn_rate if not graceful.
            :returns: None or a new FallingBox object at a random location
        """
        if self.grace_counter > 0:
            self.grace_counter -= 1
            return None

        if random.random() >= self.spawn_rate:
            return None
        else:
            ### Try to spawn a Falling Box ###
            w = game.width
            h = game.height
            rand_loc = (random.randint(0,w-1),random.randint(0,h-1))
            rand_tile = game.tiles[rand_loc[0]][rand_loc[1]]
            tries = 0
            # Try to find an empty tile
            while tries < 20 and rand_tile.has_content() and self.player_blocks_spawn(rand_tile, game.players):
                rand_loc = (random.randint(0,w-1),random.randint(0,h-1))
                rand_tile = game.tiles[rand_loc[0]][rand_loc[1]]
                tries += 1
            if not rand_tile.type == TileType.WALL and not rand_tile.has_content():
                ### Spawn Falling Box ###
                falling_box = FallingBox(rand_tile.x,rand_tile.y,FALLING_BOX_DURATION_UNTIL_CRUSH)
                rand_tile.set_content(falling_box)
                game.falling_boxes.append(falling_box)
                # Reset grace counter
                self.grace_counter = self.grace_period_ticks
                return falling_box
            else:
                return None

    def player_blocks_spawn(self, tile, players):
        if self.allow_spawn_on_player:
            return False
        return any((tile.x == x and tile.y == y for x,y in map(lambda p: p.get_tile_pos(), players)))
