import cv2
import asyncio
import websockets
import json

from collections import deque
from keras.models import load_model
import numpy as np

global cap
cap = cv2.VideoCapture(0)

global anger_detection_model # Full Keras model
anger_detection_model = load_model("angerdetect_model.h5")
# model.summary()

global FACE_MARGIN # Additional area to add to the final image around detected face
FACE_MARGIN = 22

global ANGER_HISTORY_LEN
ANGER_HISTORY_LEN = 100

global face_detector
face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

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


async def webcam_loop(websocket, path):

    global cap
    global face_detector
    global anger_detection_model
    global FACE_MARGIN
    global ANGER_HISTORY_LEN

    anger_history = deque([0 for _ in range(ANGER_HISTORY_LEN)]) # History of anger predictions

    # Get webcam image dimensions
    _, frame = cap.read()
    x_dim, y_dim = frame.shape[0:2]

    x1 = 0
    y1 = 0
    x2 = x_dim
    y2 = y_dim

    while (cap.isOpened()):
        # Capture frame-by-frame
        ret, frame = cap.read()

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
                x2 = x_dim
                x1 = x1 - (x2 - x_dim)
            if y2 > y_dim:
                y2 = y_dim
                y1 = y1 - (y2 - y_dim)

        # Crop to last known face location
        frame = frame[x1:x2,y1:y2]

        # Spread colors to full range between 0 and 1
        frame = normalize_contrast(frame)

        # Resize to target size 48x48
        frame = cv2.resize(frame,(48, 48), interpolation = cv2.INTER_CUBIC)

        # Add fake rgb for the NN input
        frame = np.array([[[entry, entry, entry] for entry in line] for line in frame])

        # Predict Anger
        prediction = anger_detection_model.predict(frame.reshape(1,48,48,3))
        predicted_anger_value = 1 if np.argmax(prediction) == 0 else 0

        # Update anger history
        anger_history.popleft()
        anger_history.append(predicted_anger_value)

        frame = cv2.resize(frame, dsize=(48*3, 48*3), interpolation=cv2.INTER_NEAREST)
        cv2.imshow("Face, greyscale, 48x48", frame)

        k = cv2.waitKey(1)
        if k == 27: # Esc
            break

        await websocket.send(json.dumps({"anger": sum(anger_history) / len(anger_history)}))

    # Cleanup
    cv2.destroyAllWindows()
    cap.release()

start_server = websockets.serve(webcam_loop, "127.0.0.1", 5678)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
