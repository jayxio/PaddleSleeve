#   Copyright (c) 2021 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Paddle Model
"""
from __future__ import absolute_import
from __future__ import print_function

from .base import Model
import paddle
import logging
logger = logging.getLogger(__name__)

import numpy as np
import os


class PaddleBlackBoxModel(Model):
    """
    PaddleBlackBoxModel
    *also support adversarial sample generation based on weighted multi-model ensemble attack.
    """
    def __init__(self,
                 model_list,
                 model_weights,
                 loss=None,
                 bounds=None,
                 channel_axis=3,
                 nb_classes=1000,
                 mean=None,
                 std=None):
        """

        Args:
            model_list:
            model_weights:
            loss:
            bounds:
            channel_axis:
            nb_classes:
            mean:
            std:
        """
        assert len(model_list) == len(model_weights)
        assert loss is not None

        super(PaddleBlackBoxModel, self).__init__(
            bounds=bounds, channel_axis=channel_axis, mean=mean, std=std)

        self._model_list = model_list
        self._model_weights = model_weights
        self._weighted_ensemble_model = self.ensemble_models(model_list, model_weights)

        self._loss = loss
        self._nb_classes = nb_classes

    def predict_name(self):
        """
        Get the predict name, such as "softmax",etc.
        :return: string
        """
        return None

    def predict(self, data):
        """
        Calculate the prediction of the data.
        Args:
            data: Numpy.ndarray Input data with shape (size, height, width, channels).
        Return:
            numpy.ndarray: Predictions of the data with shape (batch_size, num_of_classes).
        """
        # freeze BN when forwarding
        for model in self._model_list:
            for param in model.parameters():
                param.stop_gradient = True
            for module in model.sublayers():
                if isinstance(module, (paddle.nn.BatchNorm, paddle.nn.BatchNorm1D,
                                       paddle.nn.BatchNorm2D, paddle.nn.BatchNorm3D)):
                    # print("evaled!!")
                    module.eval()

        tensor_data = paddle.to_tensor(data, dtype='float32', place=self._device)
        predict = self._weighted_ensemble_model(tensor_data)

        # free model parameter
        for model in self._model_list:
            for param in model.parameters():
                param.stop_gradient = False
            for module in model.sublayers():
                if isinstance(module, (paddle.nn.BatchNorm, paddle.nn.BatchNorm1D,
                                       paddle.nn.BatchNorm2D, paddle.nn.BatchNorm3D)):
                    # print("trained!!")
                    module.train()
        return predict.numpy()

    def predict_tensor(self, data):
        """
        Calculate the prediction of the data. Usually used for compute grad for input.
        Args:
            data: Paddle.Tensor input data with shape (size, height, width, channels).
        Return:
            numpy.ndarray: predictions of the data with shape (batch_size,
                num_of_classes).
        """
        # freeze BN when forwarding
        for model in self._model_list:
            for param in model.parameters():
                param.stop_gradient = True
            for module in model.sublayers():
                if isinstance(module, (paddle.nn.BatchNorm, paddle.nn.BatchNorm1D,
                                       paddle.nn.BatchNorm2D, paddle.nn.BatchNorm3D)):
                    # print("evaled!!")
                    module.eval()

        # Run prediction
        predict = self._weighted_ensemble_model(data)

        # free model parameter
        for model in self._model_list:
            for param in model.parameters():
                param.stop_gradient = False
            for module in model.sublayers():
                if isinstance(module, (paddle.nn.BatchNorm, paddle.nn.BatchNorm1D,
                                       paddle.nn.BatchNorm2D, paddle.nn.BatchNorm3D)):
                    # print("trained!!")
                    module.train()
        return predict

    def num_classes(self):
        """
        Calculate the number of classes of the output label.
        Return:
            int: the number of classes
        """

        return self._nb_classes

    def gradient(self, data, label, optimizer=None):
        """
        Calculate the gradient of the cross-entropy loss w.r.t the image.
        Args:
            data: Numpy.ndarray input with shape as (size, height, width, channels).
            label: Int used to compute the gradient. When ensemble multi-models, keep labels consistent for all models.
            optimizer: An optimizer to compute input gradient. It should comply to different attack methods.
        Return:
            numpy.ndarray: gradient of the cross-entropy loss w.r.t the image
                with the shape (height, width, channel).
        """
        return None
