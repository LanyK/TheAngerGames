import argparse
import socket
import sys
import time
import os
from _thread import *
from enum import Enum

from GameSerializer import GameSerializer
from utils import *

import pygame

import config
from Game import Game

PACKET_SIZE = 4096


class Mode(Enum):
    STARTUP = 0
    WAITING = 1
    GAME_RUNNING = 2
    EXIT = 3


class Server:
    def __init__(self, player_port=5555, anger_port=5556, serialize=False):
        assert player_port == player_port
        self.mode = Mode.STARTUP
        self.player_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.anger_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = config.SERVER_ADRESS
        self.player_port = player_port
        self.anger_port = anger_port
        self.server_ip = socket.gethostbyname(self.address)
        # self.game = Game(file='field.json')  # TODO
        self.game = Game()
        self.reset_game_gen = self.reset_game()
        self.running = True
        self.serialize = serialize
        self.replay_dir = str(time.strftime("%Y_%d_%m-%H_%M_%S"))
        self.game_serializer = GameSerializer(self.replay_dir)

    def start(self):
        print("Server running at ", self.address)
        if self.serialize:
            try:
                os.mkdir("../replays/" + self.replay_dir)
            except OSError:
                print("Creation of replays directory failed")
        self.mode = Mode.WAITING
        start_new_thread(self.server_view, ())
        start_new_thread(self.wait_for_players, ())
        self.wait_for_anger()  # <- starts a asyncio loop: must be done from main thread
        while True:
            time.sleep(2)
            if not self.running:
                break
        print("[SERVER] <start> method ended.")

    def wait_for_anger(self):
        try:
            self.anger_socket.bind((self.address, self.anger_port))
        except:
            print("[ERROR]", sys.exc_info()[1])
            sys.exit(1)
        self.anger_socket.settimeout(0.2)
        self.anger_socket.listen(1)
        num_connections = 0
        print("[SERVER] Listening for Anger-Streaming-Server at port", self.anger_port)
        while num_connections < 1:
            if not self.running:
                self.anger_socket.close()
                break
            try:
                conn, addr = self.anger_socket.accept()
                start_new_thread(self.handle_anger_client, (conn,))
                print("[SERVER] Connected to Anger-Streaming-Server: ", addr)
                num_connections += 1
            except:
                pass
        print("[SERVER] <wait_for_anger> method ended.")

    def wait_for_players(self):
        try:
            self.player_socket.bind((self.address, self.player_port))
        except:
            print("[ERROR]", sys.exc_info()[1])
            sys.exit(1)
        self.player_socket.settimeout(0.2)
        num_players = 0
        self.player_socket.listen(2)
        print("[SERVER] Listening for Clients at port", self.player_port)
        while self.mode != Mode.EXIT and num_players < 2:  # dont search for connections when all are full
            if not self.running:
                self.player_socket.close()
                break
            try:
                conn, addr = self.player_socket.accept()
                print("[SERVER] Connected to Client: ", addr)
                start_new_thread(self.handle_player_client, (conn,))
                num_players += 1
            except:
                pass
        if self.mode != Mode.EXIT:
            self.mode = Mode.GAME_RUNNING
        print("[SERVER] <wait_for_players> thread ended.")

    def server_view(self):
        self.screen = pygame.display.set_mode((300, 300))
        pygame.display.set_caption('Server')
        self.screen.fill((0, 0, 0))
        clock = pygame.time.Clock()
        while self.running:
            clock.tick(20)
            # pygame.display.update() # we dont draw anything right now
            # exit condition
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.K_ESCAPE:
                    self.running = False
        self.mode = Mode.EXIT
        pygame.display.quit()
        pygame.quit()
        print("[SERVER] <server_view> thread ended.")

    def handle_player_client(self, conn):
        while not self.mode == Mode.EXIT:  # START NEW GAME
            ### At this point this is a connected player, but maybe the game has not started yet for lack of a second player ###
            id, _ = self.game.create_player()

            # Waiting for the server to start the game
            while self.mode != Mode.GAME_RUNNING:
                if len(self.game.players) == 2:
                    self.mode = Mode.GAME_RUNNING
                else:
                    conn.send(compress({"msg": self.mode.name}))
                    _ = conn.recv(PACKET_SIZE)

            # mode == GAME_RUNNING. Send Map first
            conn.send(compress({"msg": "MAP_DATA",
                                "id": id,
                                "f": [[(tile.type.value, tile.sprite_id) for tile in row] for row in
                                          self.game.tiles],
                                "t": [(t.x, t.y, t.ticks_to_activation) for t in self.game.spike_traps]}))
            _ = conn.recv(PACKET_SIZE)

            client_field_version = self.game.field_version

            p1, p2 = self.game.players
            conn.send(compress({
                "msg": "PLAYER_DATA", "p": [
                    {"id": 0, "x": round(p1.x, 2), "y": round(p1.y, 2), "l": p1.lifes, "b": p1.bombs, "p": p1.power},
                    {"id": 1, "x": round(p2.x, 2), "y": round(p2.y, 2), "l": p2.lifes, "b": p2.bombs, "p": p2.power}]}))
            _ = conn.recv(PACKET_SIZE)
            if id == 0 and self.serialize:
                self.game_serializer.write_header([[(tile.type.value, tile.sprite_id) for tile in row] for row in
                                                   self.game.tiles],
                                                  [(t.x, t.y, t.ticks_to_activation) for t in self.game.spike_traps], [
                                                      {"id": 0, "x": round(p1.x, 2), "y": round(p1.y, 2), "l": p1.lifes,
                                                       "b": p1.bombs, "p": p1.power},
                                                      {"id": 1, "x": round(p2.x, 2), "y": round(p2.y, 2), "l": p2.lifes,
                                                       "b": p2.bombs, "p": p2.power}])

            conn.send(compress({"msg": "GAME_START"}))  # Tells Client the game starts
            _ = conn.recv(PACKET_SIZE)

            ### ONE GAME ROUND ###
            print("[SERVER] Started game loop for player", id)

            while self.mode != Mode.EXIT:

                ### Get Client message. The client will send 1 package per Client tick ###
                data = conn.recv(PACKET_SIZE).decode()

                if data == "":
                    conn.send(compress({"msg": "CLOSE"}))
                    break
                else:
                    data = json.loads(data)

                ### If the map changed, resend map ###
                # TODO currently every send action is one Client tick. So its either map or events and never both. that should maybe be done differently, sending both map and events in one Client tick.

                if client_field_version != self.game.field_version:
                    print("[SERVER] Sending map to player", id, "FieldVersion:", self.game.field_version)
                    conn.send(compress({"msg": "MAP_DATA",
                                        "fv": self.game.field_version,
                                        "f": [[(tile.type.value, tile.sprite_id) for tile in row] for row in
                                                  self.game.tiles],
                                        "t": [(t.x, t.y, t.ticks_to_activation) for t in self.game.spike_traps]}))
                    client_field_version = self.game.field_version
                    continue

                ### ELSE process the game loop ###

                action = data["action"]
                player = self.game.players[id]

                self.game.player_action(id, action)
                self.game.update(
                    id)  # current workaround: update will pass for ID != 0 to prevent 2x game speed from happening

                new_game_events = self.game.events[id]  # get the deque for this client
                if id == 0 and self.serialize:
                    self.game_serializer.add_events(new_game_events)
                # debug start
                # print("[SERVER] Player",id," Num of events to send:",len(new_game_events))
                if len(new_game_events) > 100:
                    print("[SERVER]", [event.type for event in new_game_events])
                # debug end
                if new_game_events:
                    events_json = []
                    while new_game_events:
                        event = new_game_events.popleft()
                        events_json.append(event.encode())  # [type,data_dict]
                    data_send = {"msg": self.mode.name, "e": events_json}
                else:
                    data_sent = {"msg": self.mode.name, "e": []}

                # End loop upon win
                if not self.game.winner is None:
                    self.mode = Mode.WAITING
                    conn.send(compress({"msg": "GAME_OVER", "id": self.game.winner}))
                    break
                else:
                    conn.send(compress(data_send))

            if self.mode != Mode.EXIT:
                _ = conn.recv(4049)  # msg = "again"
                print("[SERVER] recieved again message")
                next(self.reset_game_gen)
                # start again

        print("[SERVER] <handle_player_client> thread ended.")

    def reset_game(self):
        # todo: maybe there is a not so hacky solution
        i = 0
        while True:
            if i % 2 == 0:
                self.game = Game()
                self.player_id = 0
                yield
            else:
                yield
            i += 1

    def handle_anger_client(self, conn):
        if self.serialize:
            conn.send(str.encode(json.dumps({"msg": "SERIALIZE", "replay_dir": self.replay_dir})))
        else:
            conn.send(str.encode(json.dumps({"msg": "NOT SERIALIZE"})))
        while self.mode != Mode.EXIT:
            data = json.loads(conn.recv(PACKET_SIZE).decode())
            for i in [0, 1]:
                self.game.raw_angers[i] = data[str(i)]["anger"]

        print("[SERVER] <handle_anger_client> thread ended.")


if __name__ == '__main__':
    # Parsing the command
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--player_port", help="The Port the server software should listen at. Defaults to 5555.",
                        default=5555, type=int)
    parser.add_argument("-a", "--anger_port", help="The Port the server software should listen at. Defaults to 5556.",
                        default=5556, type=int)
    parser.add_argument("-s", "--serialize", help="game_serializer",
                        default=False, action="store_true")
    args = vars(parser.parse_args())

    # Game server
    server = Server(**args)
    server.start()
