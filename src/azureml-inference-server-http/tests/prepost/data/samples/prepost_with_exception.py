import io
from typing import Dict

import numpy as np


class ModelHandler:
    def __init__(self):
        pass

    def preprocess(self, data, context: Dict) -> Dict:
        raise ZeroDivisionError("Divided by zero")

    def postprocess(self, data: Dict, context: Dict):
        raise RuntimeError("Runtime error")
