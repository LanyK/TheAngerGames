import json
import random
import socket
import time


class AngerClient:
    """
    this is a dummy anger client only for test purposes
    it sends a random walk of anger to both clients
    """

    def __init__(self, port=5556, steps=0.0001):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.host = "localhost"
        self.steps = steps
        self.port = port
        self.addr = (self.host, self.port)

    def connect(self):
        """
        connect to server
        """
        anger1 = random.random()
        anger2 = random.random()
        self.client.connect(self.addr)
        end_program = False
        while not end_program:
            anger1 += self.steps - (random.random() * self.steps * 2)
            anger2 += self.steps - (random.random() * self.steps * 2)
            if anger1 < 0:
                anger1 = 0
            if anger1 > 1:
                anger1 = 1

            if anger2 < 0:
                anger2 = 0
            if anger2 > 1:
                anger2 = 1

            try:
                self.client.send((str.encode(json.dumps({"player1": {"anger": anger1}, "player2": {"anger": anger2}}))))
                _ = self.client.recv(12288)
            except:
                end_program = True
            time.sleep(0.33)

if __name__ == '__main__':
    angerClient = AngerClient()
    angerClient.connect()
