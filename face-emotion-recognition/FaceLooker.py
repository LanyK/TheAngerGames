import cv2
import pandas as pd
import sys

import numpy as np

import keras
from keras.preprocessing.image import ImageDataGenerator
from keras import applications
from keras.layers.normalization import BatchNormalization
from keras.utils.np_utils import to_categorical

CSV_FILE="fer2013.csv"
batch_size = 64
img_width,img_height = 48,48

# 0=Angry, 1=Disgust, 2=Fear, 3=Happy, 4=Sad, 5=Surprise, 6=Neutral
num_classes = 7
reduced_num_classes = 2 # Binary: Angry or not angry
model_path = 'angerdetect_model.h5'

def load_dataset():
    # Load training and eval data
    data = pd.read_csv(CSV_FILE, sep=',') # Returns a pandas DataFrame
    train_data = data[data['Usage'] == 'Training']
    validation_data = data[data['Usage'] == 'PublicTest']
    return train_data, validation_data

def preprocess(data, label_col='emotion', feature_col='pixels'):
    labels = data.loc[:, label_col].values.astype(np.int32)
    features = [np.fromstring(image, np.float32, sep=' ') for image in data.loc[:, feature_col].values]

    labels = [keras.utils.to_categorical(l, num_classes=num_classes) for l in labels]
    # labels = [ np.array([1.,0.]) if arr[0] == 1. else np.array([0.,1.]) for arr in labels  ]

    features = np.stack((features,) * 3, axis=-1) # Shape array correctly ...
    features /= 255
    features = features.reshape(features.shape[0], img_width, img_height, 3)

    return features, labels

train_data, eval_data = load_dataset()

print("Trainshape:", train_data.shape)
print("Testshape:", eval_data.shape)

x_train, y_train = preprocess(train_data)
print("XTrainshape:",x_train.shape,"YTrainshape:",len(y_train))

x_valid, y_valid = preprocess(eval_data)
print("XValidshape:",x_valid.shape,"YValidshape:",len(y_valid))

end = False
i = 0
set = x_train
label = y_train

while not end:

    img = set[i]
    img = cv2.resize(img, dsize=(48*2, 48*2), interpolation=cv2.INTER_NEAREST)
    l = label[i]

    print(i,img.shape,l)

    cv2.imshow("Face", img)

    wait = True

    i += 1

    while wait:
        k = cv2.waitKey(100)
        if k == 27: # Esc
            end = True
            wait = False
        elif k == ord("x"):
            wait = False

# Cleanup
cv2.destroyAllWindows()
