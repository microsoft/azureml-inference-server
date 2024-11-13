# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
import uuid
import os
import time
import traceback
from datetime import datetime
from azureml_inference_server_http.api.aml_response import AMLResponse
from azureml_inference_server_http.api.aml_request import rawhttp

host_id = str(uuid.uuid4())


def init():
    print("Initializing")


@rawhttp
def run(input_data):
    print('A new request received~~~')
    try:
        start_time = time.time()
        r = dict()
        r['received_headers'] = dict()
        for k, v in input_data.headers:
            if k in r['received_headers']:
                r['received_headers'][k] = r['received_headers'][k] + ', ' + v
            else:
                r['received_headers'][k] = v

        r['received_body'] = input_data.get_data().decode('utf-8')
        r['request_info'] = {
            'host_id': host_id,
            'request_id': str(uuid.uuid4()),
            'now': datetime.now().strftime("%Y/%m/%d %H:%M:%S %f")
        }

        r['pid'] = os.getpid()
        if 'sleep-in-sec' in r['received_headers']:
            sleep = r['received_headers']['sleep-in-sec']
            print(f'sleep-in-sec: {sleep}')
            time.sleep(float(sleep))

        run_time = time.time() - start_time
        return AMLResponse(r, 200, {"pid": str(os.getpid()), "x-ms-run-function-duration": str(run_time)}, json_str=True)
    except Exception as e:
        error = str(e)
        track = traceback.format_exc()
        print(track)

        return AMLResponse({'error': error}, 500, {}, json_str=True)
