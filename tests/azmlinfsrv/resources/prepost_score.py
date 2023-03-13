import io
from typing import Dict

import numpy as np
from PIL import Image, ImageOps


class ModelHandler:
    def __init__(self):
        pass

    def preprocess(self, data, context: Dict) -> Dict:
        """
        Example preprocess method.

        Read raw bytes from the request, process the data, return KFServing input.

        Parameters:
            data (obj): the request body
            context (dict): HTTP context information

        Returns:
            dict: Json serializable KFServing input
        """
        img = Image.open(io.BytesIO(bytearray(data)))
        im_invert = ImageOps.invert(img)
        pix = np.array(im_invert, dtype=np.float32)
        pix = pix / 255.0
        reshaped_pix = pix.reshape([1, 28, 28, 1])
        return {
            "model_name": "fashion",
            "model_version": "1",
            "inputs": [
                {
                    "name": "Conv1_input",
                    "shape": [1, 28, 28, 1],
                    "datatype": "FP32",
                    "data": reshaped_pix,
                }
            ],
        }

    def postprocess(self, data: Dict, context: Dict):
        """
        Example postprocess method.

        Reshape output tensors, find the correct class name for the prediction.

        Parameters:
            data (dict): The model server response
            context (dict): HTTP context information

        Returns:
            (string/bytes, string) Json serializable string or raw bytes, response content type
        """
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
        response_type = context["headers"]["accept"]
        return prediction, response_type
