import multiprocessing
from sanic import Sanic
from azureml_inference_server_http.prepost_server import create_app

aml_app = create_app()

if __name__ == "__main__":
    # TODO: setup config values like timeouts: https://sanic.readthedocs.io/en/18.12.0/sanic/config.html
    cpu_count = 1
    aml_app.run(host="0.0.0.0", port=31311, workers=cpu_count, auto_reload=True, debug=True, access_log=True)
