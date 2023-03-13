#
# User Code
#

import io
from typing import Dict

import numpy as np
from PIL import Image, ImageOps


class ModelHandler:
    def __init__(self):
        pass

    def preprocess(self, data, context: Dict) -> Dict:
        img = Image.open(io.BytesIO(bytearray(data)))
        im_invert = ImageOps.invert(img)
        pix = np.array(im_invert, np.float32)
        pix = pix / 255.0
        data = pix.reshape([1, 28, 28, 1])
        return {
            "model_name": "fashion",
            "model_version": "3",
            "inputs": [
                {
                    "name": "Conv1_input",
                    "shape": [1, 28, 28, 1],
                    "datatype": "FP32",
                    "data": data,
                }
            ],
        }

    def postprocess(self, data: Dict, context: Dict):
        response_type = context["headers"]["accept"]
        class_names = [
            "T-shirt/top",
            "Trouser",
            "Pullover",
            "Dress",
            "Coat",
            "Sandal",
            "Shirt",
            "Sneaker",
            "Bag",
            "Ankle boot",
        ]
        reshaped = {output["name"]: np.array(output["data"]).reshape(output["shape"]) for output in data["outputs"]}
        prediction = class_names[np.argmax(reshaped["Dense"][0])]
        return prediction, response_type
