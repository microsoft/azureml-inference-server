from .constants import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_WORKER_COUNT


def run(host, port, worker_count):
    from azureml_inference_server_http.prepost_server import create_app

    aml_app = create_app()
    aml_app.run(host=host, port=port, workers=worker_count, auto_reload=False, debug=False, access_log=True)


if __name__ == "__main__":
    run(DEFAULT_HOST, DEFAULT_PORT, DEFAULT_WORKER_COUNT)
