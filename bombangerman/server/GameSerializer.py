import time


class GameSerializer:
    def __init__(self, dir_name, buffer_size=1000):
        self.rows = []
        self.buffer_size = buffer_size
        self.file_name = "../replays/" + dir_name + "/game.csv"

    def write_header(self, field, traps, player_data):
        with open(self.file_name, "a") as f:
            f.write(str(field) + "\n")
            f.write(str(traps) + "\n")
            f.write(str(player_data) + "\n")

    def add_events(self, events):
        t = time.time()
        self.rows.append((t, [x.encode() for x in events]))
        if len(self.rows) > self.buffer_size:
            with open(self.file_name, "a") as f:
                for row in self.rows:
                    f.write(";".join([str(x) for x in row]) + "\n" )
            self.rows = []
