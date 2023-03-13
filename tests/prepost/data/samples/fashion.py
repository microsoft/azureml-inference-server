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
        """
        Example preprocess method.

        Read raw bytes from the request, process the data, return KFServing input.

        Parameters:
            data (obj): the request body
            context (dict): HTTP context information

        Returns:
            dict: Json serializable KFServing input
        """
        if context["headers"]["content-type"] != "image/jpeg":
            raise RuntimeError("Incorrect content-type")
        model_version = "2" if context["headers"]["x-ms-custom"] == "model2" else "1"

        # Case where inference is skipped
        if context["headers"]["x-ms-custom"] == "skip-inference":
            context["skip-inference"] = True

        # Cases where skip_inference flag is modified
        if context["headers"]["x-ms-custom"] == "remove-skip-inference":
            context.pop("skip-inference")

        if context["headers"]["x-ms-custom"] == "mangle-skip-inference":
            context["skip-inference"] = "foo"

        img = Image.open(io.BytesIO(bytearray(data)))
        im_invert = ImageOps.invert(img)
        pix = np.array(im_invert, dtype=np.float32)
        pix = pix / 255.0
        reshaped_pix = pix.reshape([1, 28, 28, 1])  # TODO: decide whether users must make input array flat
        return {
            "model_name": "fashion",
            "model_version": model_version,
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

        response_type = context["headers"]["accept"]

        # Case where inference is skipped
        if "skip-inference" in context and context["skip-inference"] == True:
            return "inference_skipped", response_type

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
