#!/usr/bin/env python3

import sys
import cv2
import asyncio
import websockets
import json
import pygame
import time
from pygame.time import Clock
from collections import deque
from keras.models import load_model
import numpy as np
import yaml
import time
import os

# from PIL import Image

### Config ###
# TODO config file / args for the command line

with open("config.yaml", 'r') as stream:
    try:
        HOST_ADDRESS = yaml.safe_load(stream)["server_address"]
    except:
        print("config.yaml not loaded")

HOST_PORT = 5560

PATH_PREFIX = "../replays/"

global FACE_MARGIN  # Additional area to add to the final image around detected face
FACE_MARGIN = 14

### Program ###

def save_image(frame, filename):
    with open(filename, "a") as file:
        file.write(str(time.time()) + "\n")
        np.savetxt(file, (frame * 255).astype(int))
        file.write("\n")

def normalize_contrast(image):
    """ Spread brightnesses out to the full spectrum between 0 and 1
        Input shape: (x,y)
    """

    min_brightness = image.min()
    image = image - min_brightness
    max_brightness = image.max()

    factor = 1.0 / max_brightness
    image = image * factor
    return image


async def face_recognition():
    ### SETUP ###

    global cap
    global face_detector
    global anger_detection_model
    global FACE_MARGIN
    global player_id

    clock = Clock()

    # Get webcam image dimensions
    _, frame = cap.read()
    x_dim, y_dim = frame.shape[0:2]

    x1 = 0
    y1 = 0
    x2 = x_dim
    y2 = y_dim

    ### ENDLESS LOOP ###

    uri = "ws://" + str(HOST_ADDRESS) + ":" + str(HOST_PORT)

    replay_path = None

    try:
        async with websockets.connect(uri) as websocket:
            tick_no = 0
            time_stamp = str(time.strftime("%Y_%d_%m-%H_%M_%S"))

            data = await websocket.recv()
            data = json.loads(data.decode())
            if data["msg"] == "REPLAY_DIR":
                replay_path = PATH_PREFIX + data["replay_dir"] + "/faces_" + str(player_id) + ".txt"
                if os.path.isdir(PATH_PREFIX + data["replay_dir"]) == False:
                    os.mkdir(PATH_PREFIX + data["replay_dir"])

            await  websocket.send((str.encode(json.dumps({"id": 0, "anger": 0}))))

            while (
                    cap.isOpened()):  # TODO how to end the face anger sender? It is PARAMOUNT that the webcam gets released properly (see after this loop)

                clock.tick(30)
                tick_no += 1
                # print("Face FPS:", clock.get_fps())

                # Capture frame-by-frame
                ret, frame = cap.read()

                if not ret:
                    print("ERROR: Did not recieve img from capturing device (ret=False)")
                    break

                # Convert to greyscale for anger prediction
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Detect face(s)
                faces = face_detector.detectMultiScale(frame, 1.1, 2, minSize=(200, 200))

                # Uses if statement to only handle the first face. Keep in mind when testing.
                if len(faces) > 0:

                    # Get face boundary
                    y, x, h, w = faces[0]

                    # Crop to face
                    x1 = x - FACE_MARGIN
                    x2 = x + w + FACE_MARGIN
                    y1 = y - FACE_MARGIN
                    y2 = y + h + FACE_MARGIN

                    # Normalize at the edge of the image
                    if x1 < 0:
                        x1 = 0
                        x2 += abs(x1)
                    if y1 < 0:
                        y1 = 0
                        y2 += abs(y1)
                    if x2 > x_dim:
                        x1 = x1 - (x2 - x_dim)
                        x2 = x_dim
                    if y2 > y_dim:
                        y1 = y1 - (y2 - y_dim)
                        y2 = y_dim

                # Crop to last known face location
                frame = frame[x1:x2, y1:y2]

                # Resize to target size 48x48
                frame = cv2.resize(frame, (48, 48), interpolation=cv2.INTER_CUBIC)

                # Spread colors to full range between 0 and 1
                frame = normalize_contrast(frame)

                # every 15th tick (2x per second)
                if replay_path is not None and tick_no == 15:
                    save_image(frame, replay_path)
                    tick_no = 0

                # Add fake rgb for the NN input
                frame = np.stack((frame,frame,frame), axis=-1)

                # Predict Anger
                prediction = anger_detection_model.predict(frame.reshape(1, 48, 48, 3))
                predicted_anger_value = 1 if np.argmax(prediction) == 0 else 0

                k = cv2.waitKey(1)  # TODO is this desired?
                if k == 27:  # Esc
                    break

                _ = await websocket.recv()
                await  websocket.send((str.encode(json.dumps({"id": player_id, "anger": predicted_anger_value}))))

                # cv2.imshow("Face, greyscale, 48x48", cv2.resize(frame, dsize=(48*3, 48*3), interpolation=cv2.INTER_NEAREST))

            # Cleanup
            cv2.destroyAllWindows()
            cap.release()

    except Exception as e:
        print(time.time())
        raise e
    finally:
        cv2.destroyAllWindows()
        cap.release()


def main():
    ### GLOBAL SETUP ###

    global player_id

    global cap
    cap = cv2.VideoCapture(0)

    global anger_detection_model  # Full Keras model
    anger_detection_model = load_model("model/angerdetect_model_7_classes.h5")
    # model.summary()

    global face_detector
    face_detector = cv2.CascadeClassifier('model/haarcascade_frontalface_default.xml')

    ### MAIN LOOP ###

    asyncio.get_event_loop().run_until_complete(face_recognition())


if __name__ == "__main__":
    global player_id
    if len(sys.argv) < 2:
        print("[ERROR] Needs the player ID as a command line argument")
        sys.exit(1)

    player_id = int(sys.argv[1])
    main()

# open image:
# def open_image(file):
#   with open(file) as file:
#       num_images = file.read().count("\n")
#       array = np.empty((48,48))
#       for i in range(num_images):
#
#
# im = Image.fromarray(array)
# return im
