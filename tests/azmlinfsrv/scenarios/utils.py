import os
import subprocess
import requests
from datetime import datetime, timedelta
import time
from ..constants import DEFAULT_HEALTH_PORT, SERVER_COMMAND, DEFAULT_PORT, LOG_FILE, STDERR_FILE_PATH, STDOUT_FILE_PATH
from os.path import join
import re
import psutil


def get_logs(log_directory, log_filename):
    path = os.path.join(log_directory, log_filename)

    with open(path, "r", encoding="utf-8") as fh:
        return fh.readlines()


def print_logs(log_directory, log_filename):
    print("-----LOGS-----")
    print(log_filename)
    print("--------------")

    for log in get_logs(log_directory, log_filename):
        print(log)


def contains_log(log_directory, log_filename, line):
    for log in get_logs(log_directory, log_filename):
        if line in log:
            return True
    return False


def contains_log_regex(log_directory, log_filename, line, expected_output_count=0):
    for log in get_logs(log_directory, log_filename):
        matches = re.findall(line, log)
        num_matches = len(matches)
        # This conditional exists to verify double printing logs. If the number
        # of instances of log does not need to be verified, just checking for
        # existence is ok
        if num_matches > 0:
            if expected_output_count > 0:
                assert num_matches == expected_output_count
                return True
            return True
    return False


def start_server(log_directory, args, timeout=timedelta(seconds=15), port=DEFAULT_PORT, environment=None):
    stderr_file = open(os.path.join(log_directory, STDERR_FILE_PATH), "w")
    stdout_file = open(os.path.join(log_directory, STDOUT_FILE_PATH), "w")

    env = os.environ.copy()
    if environment is not None:
        env = {**env, **environment}

    server_process = subprocess.Popen([SERVER_COMMAND] + args, stdout=stdout_file, stderr=stderr_file, env=env)

    max_time = datetime.now() + timeout

    while datetime.now() < max_time:
        time.sleep(0.25)
        req = None
        try:
            req = requests.get(f"http://127.0.0.1:{port}", timeout=10)
        except Exception as e:
            print(e)

        if req != None and req.ok:
            break

        # Ensure the server is still running
        status = server_process.poll()
        if status is not None:
            break

    print_logs(log_directory, STDERR_FILE_PATH)
    print_logs(log_directory, STDOUT_FILE_PATH)

    return server_process


def score_with_post(headers=None, data=None, json=None, port=DEFAULT_PORT, stream=False):
    url = f"http://127.0.0.1:{port}/score"
    return requests.post(url=url, headers=headers, data=data, json=json, stream=stream)


def health_with_get(port=DEFAULT_HEALTH_PORT):
    url = f"http://127.0.0.1:{port}/"
    return requests.get(url=url)


def swagger_with_get(headers=None, port=DEFAULT_PORT):
    url = f"http://127.0.0.1:{port}/swagger.json"
    return requests.get(url=url, headers=headers)


def validate_server_crash(process, timeout=timedelta(seconds=5)):
    max_time = datetime.now() + timeout

    while datetime.now() < max_time:
        status = process.poll()

        # A none status indicates that the process is still running
        if status is not None:
            print(f"Server status: '{status}', Return Code: '{process.returncode}")
            assert process.returncode != 0
            return
        time.sleep(0.25)

    # Server is still running.
    assert False


def cleanup(process):
    try:
        gunicorn = psutil.Process(process.pid)

        if gunicorn.status != "terminated":
            # Kill children
            children = gunicorn.children(recursive=True)
            for child in children:
                child.kill()

            # Kill parent
            gunicorn.kill()
    except Exception as e:
        print("Failed to cleanup processes, may have crashed already.")
        print(e)
