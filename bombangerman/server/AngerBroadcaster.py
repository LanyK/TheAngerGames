import argparse
import asyncio
import json
import socket
from _thread import start_new_thread
import config

import time
import websockets


class AngerBroadcaster:
    def __init__(self, server_port=5556):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.server_host = config.SERVER_ADRESS
        self.server_port = server_port
        self.server_addr = (self.server_host, self.server_port)
        start_new_thread(self.connect_to_server, ())

        self.face_port = 5560
        self.bracelet_port = 5561
        self.angers = [0, 0]

        self.serialize = False
        self.buffer = {"ANGER": [], "GSR": [], "TEMP": [], "BVP": [], "IBI": []}
        self.buffer_size = 50
        self.replay_dir = None

        self.wait_for_face()
        self.wait_for_bracelet()

        asyncio.get_event_loop().run_forever()

        print("SHOULD NEVER HAPPEN UNLESS PROGRAM IS CANCELLED")


    def connect_to_server(self):
        """
        connect to server
        """
        self.client.connect(self.server_addr)
        end_program = False
        # Get replays dir
        resp = self.client.recv(4096).decode()
        resp = json.loads(resp)
        msg = resp.get("msg", None)
        if msg == "SERIALIZE":
            self.serialize = True
            self.replay_dir = resp.get("replay_dir")
            print("[ANGERBROADCASTER] Replays directory: ", self.replay_dir)

        # Main loop
        while not end_program:
            self.client.send((str.encode(json.dumps({"0": {"anger": self.angers[0]}, "1": {"anger": self.angers[1]}}))))
            time.sleep(0.33)
            if self.serialize:
                self.write_to_file("ANGER", "../replays/" + self.replay_dir + "/angers.csv", time.time(), self.angers[0], self.angers[1])


    def wait_for_face(self):
        server_for_face = websockets.serve(self.handle_face, self.server_host, self.face_port)
        print("[ANGERBROADCASTER] opened a Server for a Face-Client (websocket) at port", self.face_port)
        asyncio.get_event_loop().run_until_complete(server_for_face)

    def wait_for_bracelet(self):
        server_for_bracelet = websockets.serve(self.handle_bracelet, self.server_host, self.bracelet_port)
        print("[ANGERBROADCASTER] opened a Server for a Bracelet (websocket) at", self.server_host, self.bracelet_port)
        asyncio.get_event_loop().run_until_complete(server_for_bracelet)

    async def handle_bracelet(self, websocket, path):
        while True:
            data = await websocket.recv()
            data = json.loads(data.decode())
            if self.serialize:
                self.serialize_data(data)

    async def handle_face(self, websocket, path):
        try:
            if self.serialize:
                await websocket.send((str.encode(json.dumps({"msg": "REPLAY_DIR", "replay_dir": self.replay_dir}))))
            while True:
                await websocket.send((str.encode(json.dumps({"msg":"send me anger"}))))
                data = await websocket.recv()
                data = json.loads(data.decode())
                self.angers[data["id"]] = data["anger"]
        except Exception as e:
            print(time.time())
            raise e

    def serialize_data(self, data):
        # Bracelet with serial number A01026 (= 8) is for player 0, the one with serial number A00DAB is for player 1
        if data["device"] == "A01026":
            if data["type"] == "GSR":
                self.write_to_file(data["type"], "../replays/" + self.replay_dir + "/bracelet_gsr.csv", data["timestamp"], data["value"], "nan")
            if data["type"] == "TEMP":
                self.write_to_file(data["type"], "../replays/" + self.replay_dir + "/bracelet_temp.csv", data["timestamp"], data["value"], "nan")
            if data["type"] == "BVP":
                self.write_to_file(data["type"], "../replays/" + self.replay_dir + "/bracelet_bvp.csv", data["timestamp"], data["value"], "nan")
            if data["type"] == "IBI":
                self.write_to_file(data["type"], "../replays/" + self.replay_dir + "/bracelet_ibi.csv", data["timestamp"], data["value"], "nan")
        else:
            if data["type"] == "GSR":
                self.write_to_file(data["type"], "../replays/" + self.replay_dir + "/bracelet_gsr.csv", data["timestamp"], "nan", data["value"])
            if data["type"] == "TEMP":
                self.write_to_file(data["type"], "../replays/" + self.replay_dir + "/bracelet_temp.csv", data["timestamp"], "nan", data["value"])
            if data["type"] == "BVP":
                self.write_to_file(data["type"], "../replays/" + self.replay_dir + "/bracelet_bvp.csv", data["timestamp"], "nan", data["value"])
            if data["type"] == "IBI":
                self.write_to_file(data["type"], "../replays/" + self.replay_dir + "/bracelet_ibi.csv", data["timestamp"], "nan", data["value"])

    def write_to_file(self, data_type, file_name, timestamp, value1, value2):
        self.buffer[data_type].append((timestamp, value1, value2))
        if len(self.buffer[data_type]) >= self.buffer_size:
            with open(file_name, "a") as f:
                for b in self.buffer[data_type]:
                    f.write(";".join([str(x) for x in b]) + "\n")
            del self.buffer[data_type][:]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--server_port", help="The port where game listens for angerbroadcaster (should be 5556)",
                        default=5556, type=int)
    args = vars(parser.parse_args())
    anger_bro = AngerBroadcaster(**args)
