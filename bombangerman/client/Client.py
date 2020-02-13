import json
import socket
import argparse
import time
import zlib

from Player import Player
from enum import Enum
import pygame
import re
import yaml

from View import View

class Mode(Enum):
    MENU = 0
    GAME = 1
    GAME_OVER = 2

class Client:
    def __init__(self, port=5555, anger_button=True):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mode = Mode.MENU
        self.port = port
        self.id = None
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
        self.anger_button = anger_button # activate a button that is saved in file
        if self.anger_button:
            self.timeout = 0
            self.file_name = "../replays/buttonpress_" + str(time.strftime("%Y_%d_%m-%H_%M_%S")) + ".csv"

        self.view = View(32 * 15, 32 * 16, "Bombangerman")


    def run(self):
        """
        this is the main-loop of the client
        """
        clock = pygame.time.Clock()
        run = True
        playing = False

        menu = True
        ip_str = ""
        with open("config.yaml", 'r') as stream:
            try:
                ip_str = yaml.safe_load(stream)["server_address"]
            except:
                print("config.yaml not loaded")
        err = {"msg": "", "time": 0}

        ### MAIN MENU ### TODO maybe put into function to de-clutter
        while menu:
            clock.tick(30)
            # self.view.draw_init_screen("main menu", (255, 255, 255))
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.KEYUP:
                    for i, k in enumerate([pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5,
                                           pygame.K_6, pygame.K_7, pygame.K_8, pygame.K_9]):
                        if event.key == k:
                            ip_str += str(i)
                    if event.key == pygame.K_PERIOD:
                        ip_str += "."
                    if event.key == pygame.K_BACKSPACE:
                        ip_str = ip_str[0:-1]
                    if event.key == pygame.K_RETURN:
                        if re.match(r'(\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b)', ip_str):
                            try:
                                self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                self.client.settimeout(5)
                                self.client.connect((ip_str, self.port))
                                with open("config.yaml", "w") as f:
                                    yaml.dump({"server_address": ip_str}, f)
                                menu = False
                            except Exception as e:
                                self.client.close()
                                err["msg"] = "connection refused >:("
                                err["time"] = 90
                        else:
                            err["msg"] = "not a valid ip adress :("
                            err["time"] = 90
            if err["time"] == 1:
                err["msg"] = ""

            if err["time"] > 0:
                err["time"] -= 1

            self.view.draw_init_screen("Hello Client. \n\nServer Ip:" + ip_str + " \n\n(press ENTER to confirm) \n\n(leave empty for localhost) \n\n" + err["msg"], (255, 255, 255))

        while run:
            clock.tick(60)

            # always empty the queue every tick
            run = self.handle_pygame_events()

            # Communicate with Server to determine course of action
            # The server will send a msg string classifying the package
            resp = zlib.decompress(self.client.recv(4096)).decode()
            resp = json.loads(resp)
            msg = resp.get("msg", None)

            if msg == None or msg == "CLOSE":
                self.mode = Mode.MENU
                run = False
                continue

            elif msg == "STARTUP":
                self.mode = Mode.MENU
                self.send_idle_msg()

            elif msg == "WAITING":
                self.send_idle_msg()

            elif msg == "GAME_OVER":
                winner_id = resp["id"]
                self.players[not winner_id].immortal = True
                self.players[winner_id].immortal = False
                self.players[winner_id].facing = 0
                for i in range(2):
                    self.players[i].inverted_keyboard = False
                    self.players[i].autowalk = False
                    self.players[i].slimey = False
                self.mode = Mode.GAME_OVER
                self.explosions = set()
                self.boxes = set()
                self.bombs = dict()
                self.inactive_traps = dict()
                self.active_traps = set()
                self.falling_boxes = dict()
                self.crushing_boxes = dict()
                self.active_taunts = dict()
                self.power_ups = dict()
                playing = False
                waiting_screen = True
                while waiting_screen:
                    clock.tick(30)
                    winner_color = "blue" if resp["id"] == 0 else "red"
                    color = (0,0,255) if resp["id"] == 0 else (255,0,0)
                    s = "the " + winner_color + " player won! \n \n press 'R' to play again"
                    self.view.draw_game_over_screen(self.players, self.id, s, color)
                    _ = pygame.event.get()
                    keys = pygame.key.get_pressed()
                    if keys[pygame.K_r]:
                        self.mode = Mode.MENU
                        waiting_screen = False
                    #self.view.draw_players(resp["you"], resp["other"], self.id)
                    self.view.update()
                self.client.send(str.encode(json.dumps({"msg": "again"})))

            elif msg == "GAME_START":
                if self.field == None or self.players == None:
                    raise ValueError("Server sent",msg,"when Client has not Map or Player data.")
                if not playing:
                    playing = True
                    self.mode = Mode.GAME
                else:
                    raise ValueError("Server sent",msg,"when Client is already in-game.")
                self.send_idle_msg() # Sends 2x to switch roles of initiative with the server
                self.send_action("wait")

            elif msg == "GAME_RUNNING":
                if not playing:
                    raise ValueError("Server sent",msg,"when Client is not in-game.")
                action = self.handle_user_input()
                self.handle_server_events(resp)
                self.send_action(action)

            elif msg == "MAP_DATA":
                self.id = resp["id"]
                self.field = resp["f"]
                for x,y,ticks in resp["t"]:
                    self.inactive_traps[(x,y)] = [ticks,ticks]
                self.send_idle_msg()

            elif msg == "PLAYER_DATA":
                player_data = resp["p"]
                self.update_player_data(player_data)
                self.send_idle_msg()

            elif msg == "EXIT":
                run = False
                continue
            else:
                raise NotImplementedError("Server msg",msg,"handling is not implemented in the .run() method of the Client")

            ### DRAW PYGAME SCREEN ###

            if self.mode == Mode.MENU:
                #self.view.draw_menu() # TODO
                self.view.draw_init_screen(resp["msg"], (255,255,255))
            elif self.mode == Mode.GAME:
                self.update_counters()
                self.view.draw_game(self.field, self.boxes, self.inactive_traps, self.active_traps, self.power_ups, self.bombs, self.explosions, self.falling_boxes, self.crushing_boxes, self.players, self.active_taunts, self.id, clock)
            elif self.mode == Mode.GAME_OVER: # TODO currently unused
                self.view.draw_game_over()

        pygame.quit()

    def update_counters(self):
        """ Updates all tick counters for the client
        """
        for bomb in self.bombs:
            self.bombs[bomb] -= 1

        for x,y in self.inactive_traps:
            data = self.inactive_traps[(x,y)]
            data[1] -= 1 # [max_ticks, remaining_ticks]

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


    def send_idle_msg(self):
        self.client.send(str.encode(json.dumps({"msg": "ok"})))

    def send_action(self, action:str):
        data = {"id": self.id, "action": action}
        self.client.send(str.encode(json.dumps(data)))

    def handle_server_events(self, resp:dict):
        for type, data in resp.get("e",[]):
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
                self.players[data["id"]].bloody = 32
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
                self.boxes.add((data["x"],data["y"]))
            elif type == 6:
                # SPAWN_BOMB
                self.bombs[(data["x"],data["y"])] = data["t"] # x,y -> ticks
            elif type == 7:
                # SPAWN_EXPLOSION
                self.explosions.add((data["x"],data["y"]))
            elif type == 8:
                # UPDATE_TRAP
                # unused
                pass
            elif type == 9:
                # REMOVE_BOX
                self.boxes.discard((data["x"],data["y"]))
            elif type == 10:
                # REMOVE_BOMB
                self.bombs.pop((data["x"],data["y"]), None)
            elif type == 11:
                # REMOVE_EXPLOSION
                self.explosions.discard((data["x"],data["y"]))
            elif type == 15:
                # SPAWN_FALLING_BOX
                self.falling_boxes[(data["x"],data["y"])] = data["t"] # x,y -> ticks
            elif type == 16:
                # REMOVE_FALLING_BOX
                self.falling_boxes.pop((data["x"],data["y"]), None)
            elif type == 17:
                # SPAWN_CRUSHING_BOX
                self.crushing_boxes[(data["x"],data["y"])] = data["t"]
            elif type == 18:
                # REMOVE_CRUSHING_BOX
                self.crushing_boxes.pop((data["x"],data["y"]), None)
            elif type == 19:
                # PLAYER_TAUNT
                if data["id"] not in self.active_taunts:
                    self.active_taunts[data["id"]] = data["t"]
            elif type == 20:
                # SPAWN_POWER_UP
                self.power_ups[(data["x"],data["y"])] = data["t"] # type
            elif type == 21:
                # REMOVE_POWER_UP
                self.power_ups.pop((data["x"],data["y"]), None)
            elif type == 22:
                # ANGER_INFO
                self.players[0].set_anger(data["0"])
                self.players[1].set_anger(data["1"])
            elif type == 23:
                # ACTIVATE_TRAP
                self.inactive_traps.pop((data["x"],data["y"]), None)
                self.active_traps.add((data["x"],data["y"]))
            elif type == 24:
                # RESET_TRAP
                self.inactive_traps[(data["x"],data["y"])] = [data["t"],data["t"]] # [max_ticks, remaining_ticks]
                self.active_traps.discard((data["x"],data["y"]))
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

    def handle_user_input(self):
        # get pressed key
        keys = pygame.key.get_pressed()
        action = "wait"  # default action

        # map pressed key to an action
        if keys[pygame.K_l]:
            action = "right"
        elif keys[pygame.K_j]:
            action = "left"
        elif keys[pygame.K_i]:
            action = "up"
        elif keys[pygame.K_k]:
            action = "down"
        if keys[pygame.K_o]:
            action = "slime"
        if keys[pygame.K_u]:
            action = "taunt"
        if keys[pygame.K_SPACE]:
            action = "bomb"
        if self.anger_button:
            if keys[pygame.K_a]:
                if self.timeout == 0:
                    with open(self.file_name, "a") as f:
                        f.write(str(time.time()) + "\n")
                    self.timeout += 100
            if self.timeout > 0:
                self.timeout -= 1
        return action

    def handle_pygame_events(self):
        run = True
        for event in pygame.event.get(): # pops events from the queue
            if event.type == pygame.MOUSEMOTION: # TODO rly do this in the menu too?
                if self.view.slimy:
                    x, y = pygame.mouse.get_pos()
                    self.view.remove_slime(x,y)
            if event.type == pygame.QUIT:
                run = False
            if event.type == pygame.K_ESCAPE:
                run = False
        return run

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
                self.players[pid] = Player(pid,x,y,lifes,power,bombs)
            else:
                player.x = x
                player.y = y
                player.lifes = lifes
                player.bombs = bombs
                player.power = power

if __name__ == '__main__':
    # Parsing the command
    pygame.init()
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", help="Port of the game server to connect to. Defaults to 5555.", default=5555,
                        type=int)
    args = vars(parser.parse_args())

    # Game Client
    client = Client(**args)
    client.run()
