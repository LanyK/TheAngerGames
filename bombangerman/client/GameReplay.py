import argparse
from math import sqrt, floor, ceil
from os import listdir
import io

from Player import Player
import pygame
import time
from View import View
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import cv2

BUTTONPRESS_CSV = "buttonpress.csv"
GAME_CSV = "game.csv"
FACE_FILES = ["faces_0.txt", "faces_1.txt"]

class DummyClock:
    def __init__(self):
        pass

    def get_fps(self):
        return 60

    def get_rawtime(self):
        return 1

    def get_time(self):
        return 1


class GameReplay:
    def __init__(self, replay_dir):
        self.field = None
        self.players = []
        self.boxes = set()
        self.bombs = dict()
        self.explosions = set()
        self.inactive_traps = dict()
        self.active_traps = set()
        self.falling_boxes = dict()
        self.crushing_boxes = dict()
        self.power_ups = dict()
        self.active_taunts = dict()
        self.view = View(32 * 15, 32 * 16, "Replay Bombangerman")
        self.plots = []
        self.vlines = []
        self.replay_dir = "../replays/" + replay_dir
        self.face_replay_file_handles = [None,None]
        self.next_faces = [[0,np.zeros((48,48))],[0,np.zeros((48,48))]]

        plt.ion()
        plt.show()
        self.figure = plt.figure()
        self.figure.autofmt_xdate()
        plt.xticks([])
        plt.yticks([])

        self.last_timestamp = None
        self.first_timestamp = None
        replay_files = listdir(self.replay_dir)

        if GAME_CSV in replay_files:
            with open(self.replay_dir + "/" + GAME_CSV) as f:
                lines = f.readlines()
                self.first_timestamp = float(lines[3].split(";")[0])
                self.last_timestamp = float(lines[-1].split(";")[0])

        # plot data files
        data_files = [f for f in replay_files if f not in [GAME_CSV, BUTTONPRESS_CSV] + FACE_FILES]
        self.nr_plots = len(data_files)
        for file in data_files:
            print("FILENAME:", file)
            self.replay_data(file)

        # Faces Replay display setup
        # Yes, this has constantly open file handles. but this is read only, so we will prolly get away with it.
        # Here, we preload the first entry in those files
        for i,filename in enumerate(FACE_FILES):
            if filename in replay_files:
                f = open(self.replay_dir + "/" + filename)
                self.face_replay_file_handles[i] = f
                print("Opened Face Data File for Player", i)
                self.load_next_image_and_timestamp(i,f)
        # prepare 2 windows if 2 players have replay data here
        for i,h in enumerate(self.face_replay_file_handles):
            if h is not None:
                cv2.namedWindow("Player " + str(i))

        # buttonpress
        if BUTTONPRESS_CSV in replay_files:
            try:
                with open(self.replay_dir + "/" + BUTTONPRESS_CSV) as f:
                    content = f.readlines()

                bps = [float(x) for x in content]

                for b in bps:
                    for plot in self.plots:
                        plot.axvline(x=b, c="b")
            except FileNotFoundError:
                print(BUTTONPRESS_CSV + " not found")

        # game replay
        if GAME_CSV in replay_files:
            with open(self.replay_dir + "/" + GAME_CSV) as f:
                for i, line in enumerate(f):
                    if i == 0:
                        self.field = eval(line)
                    elif i == 1:
                        for x, y, ticks in eval(line):
                            self.inactive_traps[(x, y)] = [ticks, ticks]
                    elif i == 2:
                        player_data = eval(line)
                        self.update_player_data(player_data)
                    else:
                        break

    def replay_data(self, filename):
        content = pd.read_csv(self.replay_dir + "/" + filename, delimiter=";", names=["time", "player0", "player1"], dtype="float")
        if self.last_timestamp is not None:
            content = content[content["time"] <= self.last_timestamp]
        if self.first_timestamp is not None:
            content = content[content["time"] >= self.first_timestamp]
        content = content.fillna(method='ffill').dropna()
        content = content.sort_values('time', axis=0)

        plot_nr = len(self.plots) + 1

        nr_rows = ceil(sqrt(self.nr_plots))
        nr_columns = ceil(sqrt(self.nr_plots))

        plot = self.figure.add_subplot(nr_rows, nr_columns, plot_nr)
        plot.title.set_text(filename)
        self.plots.append(plot)
        content.plot(x="time", ax=plot)
        vline = plot.axvline(x=0, c="r")
        self.vlines.append(vline)

    def new_plot(self, x, ys, title):
        plot_nr = len(self.plots) + 1

        nr_rows = floor(sqrt(self.nr_plots))
        nr_columns = ceil(sqrt(self.nr_plots))

        plot = self.figure.add_subplot(nr_rows, nr_columns, plot_nr)
        plot.title.set_text(title)
        self.plots.append(plot)
        for y in ys:
            plot.plot(x, y)
        vline = plot.axvline(x=x[0], c="r")
        self.vlines.append(vline)

    def replay(self):
        clock = DummyClock()
        run = True
        frame = 3
        last_timestamp = None
        while run:

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    run = False
                if event.type == pygame.K_ESCAPE:
                    run = False

            with open(self.replay_dir + "/" + GAME_CSV) as f:
                for i, line in enumerate(f):
                    if i == frame:
                        if line == "\n": # no idea why but needed in windows
                            continue
                        timestamp = eval(line.split(";")[0])

                        events = eval(line.split(";")[1])
                        self.handle_events(events)
                    elif i < frame:
                        continue
                    else:
                        break
                        
            if frame % 30 == 0:
                for vline in self.vlines:
                    vline.set_xdata(timestamp)
                # TODO what's this line for?
                plt.pause(1e-10)

            if not last_timestamp is None:
                time.sleep((timestamp - last_timestamp)/5)

            last_timestamp = timestamp

            # intermission: draw player face when present
            for i,h in enumerate(self.face_replay_file_handles):
                if h is not None:
                    if timestamp >= self.next_faces[i][0]:
                        img = self.next_faces[i][1] / 255.0
                        img = cv2.resize(img, dsize=(48*3, 48*3), interpolation=cv2.INTER_NEAREST)
                        cv2.imshow("Player " + str(i), img)
                        self.load_next_image_and_timestamp(i,h)
            # intermission end

            self.update_counters()
            self.view.draw_game(self.field, self.boxes, self.inactive_traps, self.active_traps, self.power_ups,
                                self.bombs, self.explosions, self.falling_boxes, self.crushing_boxes,
                                self.players, self.active_taunts, 0, clock)
            self.view.update()
            frame += 1

        pygame.quit()

    def update_counters(self):
        """ Updates all tick counters for the client
        """
        for bomb in self.bombs:
            self.bombs[bomb] -= 1

        for x, y in self.inactive_traps:
            data = self.inactive_traps[(x, y)]
            data[1] -= 1  # [max_ticks, remaining_ticks]

        for falling_box in self.falling_boxes:
            self.falling_boxes[falling_box] -= 1

        for crushing_box in self.crushing_boxes:
            self.crushing_boxes[crushing_box] -= 1

        remove = []
        for id, ticks in self.active_taunts.items():
            if ticks <= 0:
                remove.append(id)
            else:
                self.active_taunts[id] -= 1
        for id in remove:
            del self.active_taunts[id]

    def update_player_data(self, player_data):
        while len(self.players) < len(player_data):
            self.players.append(None)
        for d in player_data:
            pid = d["id"]
            x = d["x"]
            y = d["y"]
            lifes = d["l"]
            bombs = d["b"]
            power = d["p"]
            player = self.players[pid] if len(self.players) > pid else None
            if player == None:
                self.players[pid] = Player(pid, x, y, lifes, power, bombs)
            else:
                player.x = x
                player.y = y
                player.lifes = lifes
                player.bombs = bombs
                player.power = power

    def handle_events(self, events):
        for type, data in events:
            if type == 0:
                # GENERIC
                pass
            elif type == 1:
                # PLAYER_INIT
                # unused
                pass
            elif type == 2:
                # PLAYER_MORTAL
                self.players[data["id"]].immortal = False
            elif type == 3:
                # PLAYER_DAMAGED
                self.players[data["id"]].lifes -= data["dmg"]
                self.players[data["id"]].immortal = True
            elif type == 4:
                # PLAYER_MOVED
                p = self.players[data["id"]]
                p.x = data["x"]
                p.y = data["y"]
                p.facing = data["f"]
            elif type == 12:
                # PLAYER_NOT_SLIMEY
                self.players[data["id"]].slimey = False
            elif type == 13:
                # PLAYER_SLIMED
                self.players[data["id"]].slimey = True
            elif type == 5:
                # SPAWN_BOX
                self.boxes.add((data["x"], data["y"]))
            elif type == 6:
                # SPAWN_BOMB
                self.bombs[(data["x"], data["y"])] = data["t"]  # x,y -> ticks
            elif type == 7:
                # SPAWN_EXPLOSION
                self.explosions.add((data["x"], data["y"]))
            elif type == 8:
                # UPDATE_TRAP
                # unused
                pass
            elif type == 9:
                # REMOVE_BOX
                self.boxes.discard((data["x"], data["y"]))
            elif type == 10:
                # REMOVE_BOMB
                self.bombs.pop((data["x"], data["y"]), None)
            elif type == 11:
                # REMOVE_EXPLOSION
                self.explosions.discard((data["x"], data["y"]))
            elif type == 15:
                # SPAWN_FALLING_BOX
                self.falling_boxes[(data["x"], data["y"])] = data["t"]  # x,y -> ticks
            elif type == 16:
                # REMOVE_FALLING_BOX
                self.falling_boxes.pop((data["x"], data["y"]), None)
            elif type == 17:
                # SPAWN_CRUSHING_BOX
                self.crushing_boxes[(data["x"], data["y"])] = data["t"]
            elif type == 18:
                # REMOVE_CRUSHING_BOX
                self.crushing_boxes.pop((data["x"], data["y"]), None)
            elif type == 19:
                # PLAYER_TAUNT
                if data["id"] not in self.active_taunts:
                    self.active_taunts[data["id"]] = data["t"]
            elif type == 20:
                # SPAWN_POWER_UP
                self.power_ups[(data["x"], data["y"])] = data["t"]  # type
            elif type == 21:
                # REMOVE_POWER_UP
                self.power_ups.pop((data["x"], data["y"]), None)
            elif type == 22:
                # ANGER_INFO
                self.players[0].set_anger(data["0"])
                self.players[1].set_anger(data["1"])
            elif type == 23:
                # ACTIVATE_TRAP
                self.inactive_traps.pop((data["x"], data["y"]), None)
                self.active_traps.add((data["x"], data["y"]))
            elif type == 24:
                # RESET_TRAP
                self.inactive_traps[(data["x"], data["y"])] = [data["t"], data["t"]]  # [max_ticks, remaining_ticks]
                self.active_traps.discard((data["x"], data["y"]))
            elif type == 25:
                # PLAYER_INVERT_KEYBOARD_ON
                self.players[data["id"]].inverted_keyboard = True
            elif type == 26:
                # PLAYER_INVERT_KEYBOARD_OFF
                self.players[data["id"]].inverted_keyboard = False
            elif type == 27:
                # PLAYER_CHANGE_BOMBS_COUNT
                self.players[data["id"]].bombs = data["b"]
            elif type == 28:
                # PLAYER_CHANGE_POWER_AMOUNT
                self.players[data["id"]].power = data["p"]
            elif type == 29:
                # PLAYER_AUTOWALK_ON
                self.players[data["id"]].autowalk = True
            elif type == 30:
                # PLAYER_AUTOWALK_OFF
                self.players[data["id"]].autowalk = False

    def load_next_image_and_timestamp(self, player_id, opened_handle):
        f = opened_handle
        timestamp = f.readline()
        if timestamp == "":
            self.face_replay_file_handles[player_id] = None
            f.close()
            return
        else:
            # print([timestamp])
            timestamp = float(timestamp)
            self.next_faces[player_id][0] = timestamp
            image_data = []
            for _ in range(48):
                line = f.readline()
                if line == "":
                    self.face_replay_file_handles[player_id] = None
                    f.close()
                    return
                image_data.append(line.strip())
            print(len(image_data))
            image_data = "\n".join(image_data)
            image_data = io.StringIO(initial_value=image_data.strip() + "\n")
            img = np.loadtxt(image_data)
            self.next_faces[player_id][1] = img
            line = f.readline().strip()
            if line != "":
                print(line)
                print("ERROR: Wanted to jump empty line but was not empty")




if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--replay_dir", help="The directory containing the replays for this run.", type=str)
    args = vars(parser.parse_args())

    gr = GameReplay(**args)
    gr.replay()
