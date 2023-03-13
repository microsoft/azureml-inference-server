from sanic.exceptions import SanicException, InvalidUsage


class UserCodeException(InvalidUsage):
    """
    A class to represent a user's code runtime exception
    """

    def __init__(self, message):
        SanicException.__init__(self, message, status_code=500)
        self.message = message


class UserCodeConfigurationException(SanicException):
    """
    A class to represent a user's code configuration exception
    """

    def __init__(self, message):
        SanicException.__init__(self, message)
        self.message = message


class DeploymentConfigurationException(SanicException):
    """
    A class to represent a deployment configuration exception
    """

    def __init__(self, message):
        SanicException.__init__(self, message)
        self.message = message


class TritonInferenceException(SanicException):
    """
    A class to represent a Triton Inference exception
    """

    def __init__(self, message, status_code=500):
        SanicException.__init__(self, message, status_code=status_code)
        self.message = message
