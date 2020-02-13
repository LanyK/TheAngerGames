import json
import zlib


def compress(data):
    return zlib.compress(str.encode(json.dumps(data)))
