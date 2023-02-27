import json


def init():
    print("User init function invoked.")
    pass


"""
Simple run function that echoes the input data.
"""


def run(input_data):
    print("User run function invoked.")
    return json.loads(input_data)
