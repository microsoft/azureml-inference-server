""" Utility functions """
import time


def capture_time_taken_async(func):
    """Captures time taken in milliseconds to run a function."""

    async def timer(*args, **kwargs):
        t1 = time.perf_counter()
        result = await func(*args, **kwargs)
        t2 = time.perf_counter()
        # convert to milliseconds
        time_taken = (t2 - t1) * 1000
        return result, time_taken

    return timer


def capture_time_taken(func):
    """ "Captures time taken in milliseconds to run a function."""

    def timer(*args, **kwargs):
        t1 = time.perf_counter()
        result = func(*args, **kwargs)
        t2 = time.perf_counter()
        # convert to milliseconds
        time_taken = (t2 - t1) * 1000
        return result, time_taken

    return timer
