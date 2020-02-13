#!/usr/bin/env python3

import keras
from keras.models import Sequential
from keras.layers import Conv2D, MaxPooling2D, AveragePooling2D
from keras.layers import Activation, Dropout, Flatten, Dense
from keras.preprocessing.image import ImageDataGenerator
from keras import applications
from keras.layers.normalization import BatchNormalization
import numpy as np
from keras.utils.np_utils import to_categorical
from keras.layers import Conv2D, MaxPooling2D, Input
from keras.models import Model
from keras.callbacks import TensorBoard
import pandas as pd

CSV_FILE="./fer2013/fer2013.csv"
batch_size = 64
img_width,img_height = 48,48

num_classes = 7 # 0=Angry, 1=Disgust, 2=Fear, 3=Happy, 4=Sad, 5=Surprise, 6=Neutral
reduced_num_classes = 2 # Binary: Angry or not angry
model_path = 'angerdetect_model_7_bigdeep.h5'

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
    labels = [ np.array([1.,0.]) if arr[0] == 1. else np.array([0.,1.]) for arr in labels  ]

    features = np.stack((features,) * 3, axis=-1) # Shape array correctly ...
    features /= 255
    features = features.reshape(features.shape[0], img_width, img_height, 3)

    return features, labels

# Load FER dataset
train_data, eval_data = load_dataset()

# preprocess FER dataset
x_train, y_train = preprocess(train_data)
x_valid, y_valid = preprocess(eval_data)

print(x_train.shape[0], 'train samples')
print(x_valid.shape[0], 'valid samples')

gen = ImageDataGenerator(
        rotation_range=40,
        width_shift_range=0.2,
        height_shift_range=0.2,
        shear_range=0.2,
        zoom_range=0.2,
        horizontal_flip=True,
        fill_mode='nearest')

train_generator = gen.flow(x_train, y_train, batch_size=batch_size)
predict_size_train = int(np.math.ceil(len(x_train) / batch_size))

gen = ImageDataGenerator()
valid_generator = gen.flow(x_valid, y_valid, batch_size=batch_size)
predict_size_valid = int(np.math.ceil(len(x_valid) / batch_size))

model = Sequential()
model.add(Conv2D(36, (3, 3), padding='same', input_shape=(img_width, img_height, 3)))
model.add(Activation('relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))
model.add(Dropout(0.4))

model.add(Conv2D(50,(3, 3), padding='same'))
model.add(Activation('relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))
model.add(Dropout(0.4))

model.add(Conv2D(100,(3, 3), padding='same'))
model.add(Activation('relu'))
model.add(MaxPooling2D(pool_size=(2, 2)))
model.add(Dropout(0.4))

model.add(Flatten())  # convert to 1D to allow input in standard Feedforward Network
model.add(Dense(250))
model.add(Dropout(0.5))
model.add(Dense(2))
model.add(Activation('softmax'))

model.compile(loss='categorical_crossentropy', optimizer=keras.optimizers.Adam(lr=0.0005), metrics=['accuracy'])

model.summary()

saving_callback = keras.callbacks.ModelCheckpoint(model_path,
                                                  monitor='val_loss',
                                                  verbose=1,
                                                  save_best_only=True,
                                                  save_weights_only=False,
                                                  mode='auto',
                                                  period=1)

model.fit_generator(train_generator,
                    steps_per_epoch=predict_size_train * 4, # Let the generastor create 5x the train set of slight variations
                    epochs=40 ,
                    class_weight={0:2,1:0.3}, # Combat data set inequality
                    validation_data=valid_generator,
                    validation_steps=predict_size_valid,
                    callbacks=[saving_callback])
