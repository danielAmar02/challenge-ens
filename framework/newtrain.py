########## Work In progress ### 


from gen_patches import *

import os.path
import numpy as np
import tifffile as tiff
from keras.callbacks import CSVLogger
from keras.callbacks import TensorBoard
from keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from pathlib import Path
import datetime
import argparse
import yaml
import random
import numpy as np
import pandas as pd
import tensorflow as tf

from dataset import LandCoverData as LCD
from dataset import parse_image, load_image_train, load_image_test
from model import UNet
from tensorflow_utils import plot_predictions
from utils import YamlNamespace
from os import path


if not path.exists('/content/experiments'):
  Save_model='/content/experiments'
  os.mkdir(Save_model)


def normalize(img):
    min = img.min()
    max = img.max()
    x = 2.0 * (img - min) / (max - min) - 1.0
    return x
  
  


def _parse_args():
    parser = argparse.ArgumentParser('Training script')
    parser.add_argument('--config', '-c', type=str, required=True, help="The YAML config file")
    cli_args = parser.parse_args()
    # parse the config file
    with open(cli_args.config, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    config = YamlNamespace(config)
    config.xp_rootdir = Path(config.xp_rootdir).expanduser()
    assert config.xp_rootdir.is_dir()
    config.dataset_folder = Path(config.dataset_folder).expanduser()
    assert config.dataset_folder.is_dir()
    if config.val_samples_csv is not None:
        config.val_samples_csv = Path(config.val_samples_csv).expanduser()
        assert config.val_samples_csv.is_file()

    return config

if __name__ == '__main__':


    N_BANDS = 8
    N_CLASSES = 10 # buildings, roads, trees, crops and water
    CLASS_WEIGHTS = [0.2, 0.3, 0.1, 0.1, 0.3]
    N_EPOCHS = 2
    UPCONV = True
    PATCH_SZ = 160   # should divide by 16
    BATCH_SIZE = 32
    TRAIN_SZ = 15000  # train size
    VAL_SZ = 3000    # validation size


    def get_model():
        return unet_model(N_CLASSES, PATCH_SZ, n_channels=N_BANDS, upconv=UPCONV, class_weights=CLASS_WEIGHTS)


    weights_path = 'weights'
    if not os.path.exists(weights_path):
        os.makedirs(weights_path)
    weights_path += '/unet_weights.hdf5'

    trainIds = [str(i).zfill(2) for i in range(1, 25)]  # all availiable ids: from "01" to "24"


    if __name__ == '__main__':
        X_DICT_TRAIN = dict()
        Y_DICT_TRAIN = dict()
        X_DICT_VALIDATION = dict()
        Y_DICT_VALIDATION = dict()

        print('Reading images')
        for img_id in trainIds:
            img_m = normalize(tiff.imread('./data/mband/{}.tif'.format(img_id)).transpose([1, 2, 0]))
            mask = tiff.imread('./data/gt_mband/{}.tif'.format(img_id)).transpose([1, 2, 0]) / 255
            train_xsz = int(3/4 * img_m.shape[0])  # use 75% of image as train and 25% for validation
            X_DICT_TRAIN[img_id] = img_m[:train_xsz, :, :]
            Y_DICT_TRAIN[img_id] = mask[:train_xsz, :, :]
            X_DICT_VALIDATION[img_id] = img_m[train_xsz:, :, :]
            Y_DICT_VALIDATION[img_id] = mask[train_xsz:, :, :]
            print(img_id + ' read')
        print('Images were read')

        def train_net():
            print("start train net")
            x_train, y_train = get_patches(X_DICT_TRAIN, Y_DICT_TRAIN, n_patches=TRAIN_SZ, sz=PATCH_SZ)
            x_val, y_val = get_patches(X_DICT_VALIDATION, Y_DICT_VALIDATION, n_patches=VAL_SZ, sz=PATCH_SZ)
            model = get_model()
            if os.path.isfile(weights_path):
                model.load_weights(weights_path)
            #model_checkpoint = ModelCheckpoint(weights_path, monitor='val_loss', save_weights_only=True, save_best_only=True)
            #early_stopping = EarlyStopping(monitor='val_loss', min_delta=0, patience=10, verbose=1, mode='auto')
            #reduce_lr = ReduceLROnPlateau(monitor='loss', factor=0.1, patience=5, min_lr=0.00001)
            model_checkpoint = ModelCheckpoint(weights_path, monitor='val_loss', save_best_only=True)
            csv_logger = CSVLogger('log_unet.csv', append=True, separator=';')
            tensorboard = TensorBoard(log_dir='./tensorboard_unet/', write_graph=True, write_images=True)
            model.fit(x_train, y_train, batch_size=BATCH_SIZE, epochs=N_EPOCHS,
                      verbose=2, shuffle=True,
                      callbacks=[model_checkpoint, csv_logger, tensorboard],
                      validation_data=(x_val, y_val))
            return model

        train_net()
