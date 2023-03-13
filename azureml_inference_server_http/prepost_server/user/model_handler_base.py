class ModelHandlerBase:
    def __init__(self):
        pass

    def preprocess(self, data, context):
        """
        Example preprocess method.

        Read raw bytes from the request, process the data, return KFServing input.

        Parameters:
            data (obj): the request body
            context (dict): HTTP context information

        Returns:
            dict: Json serializable KFServing input
        """
        print("[[[ModelHandlerBase]]] pre-processing")

    def postprocess(self, data, context):
        """
        Example postprocess method.

        Reshape output tensors, find the correct class name for the prediction.

        Parameters:
            data (dict): The model server response
            context (dict): HTTP context information

        Returns:
            (string/bytes, string) Json serializable string or raw bytes, response content type
        """
        print("[[[ModelHandlerBase]]] post-processing")
