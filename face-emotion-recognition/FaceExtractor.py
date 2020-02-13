import cv2

from keras.models import load_model
import numpy as np
import time

FACE_MARGIN = 22

cap = cv2.VideoCapture(0)

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier('haarcascade_eye.xml')

_, frame = cap.read()
x_dim, y_dim = frame.shape[0:2]

## Keras Model
model = load_model("angerdetect_model.h5")
model.summary()

angry_count = 0

x1 = 0
y1 = 0
x2 = x_dim
y2 = y_dim

print("starting cam...\n")

while (cap.isOpened()):

    # Capture frame-by-frame
    ret, frame = cap.read()

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 2, minSize=(200, 200))

    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if len(faces) > 0:
    # 1 Face only allowed!
        x, y, w, h = faces[0]
        # cv2.rectangle(frame, (x, y), (x + 2, y + 2), (255, 0, 0), 2) # red
        # cv2.rectangle(frame, (x, y + h), (x + 2, y + h + 2), (0, 255, 0), 2) # green
        # cv2.rectangle(frame, (x + w, y), (x + w + 2, y + 2), (0, 0, 255), 2) # blue
        # cv2.rectangle(frame, (x + w, y + h), (x + w + 2, y + h + 2), (255, 0, 255), 2) # purple

        # Crop to face
        # !! Face x y and image x y are switched for some reason
        x1 = y - FACE_MARGIN
        x2 = y + h + FACE_MARGIN
        y1 = x - FACE_MARGIN
        y2 = x + w + FACE_MARGIN

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

        frame = frame[x1:x2,y1:y2]

        remaining_x_dim, remaining_y_dim = x2 - x1, y2 - y1

        # spread brightnesses 0 <-> 1
        min_brightness = frame.min()
        frame = frame - min_brightness
        max_brightness = frame.max()

        factor = 1.0 / max_brightness
        frame = frame * factor

        min_brightness = frame.min()
        max_brightness = frame.max()


        #print(min_brightness, median, max_brightness)
        #   |
        # x V
        #
        # y ->

        # Resize
    else:
        # No faces found, approximate by extracting the last known face position of the image and hope for the best
        frame = frame[x1:x2,y1:y2]

    frame = cv2.resize(frame,(48, 48), interpolation = cv2.INTER_CUBIC)

    frame = np.array([[[entry, entry, entry] for entry in line] for line in frame])

    angry = False

    if np.argmax(model.predict(frame.reshape(1,48,48,3))) == 0:
        angry = True

    print("\r        ", end="")
    print("\r" + str(angry), end="")

    cv2.imshow("Face, greyscale, 48x48", frame)

    k = cv2.waitKey(1)
    if k == 27: # Esc
        break
    if k == ord("c"):
        with open("images/" + str(time.time()) + "_" + ("1" if angry else "0") + ".nptxt",  "w") as f:
            np.savetxt(f, frame.reshape(48,48,3)[:,:,1].reshape(48,48))

# Cleanup
print("\nexiting...")
cv2.destroyAllWindows()
cap.release()
