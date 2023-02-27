import pytest


def test_concurrent_requests(app, basic_headers, pullover_bytes):
    custom_headers = basic_headers.copy()
    custom_headers["x-ms-custom"] = "model2"
    custom_headers["x-ms-log-level"] = "debug"
    basic_headers["x-ms-log-level"] = "critical"
    _, resp1 = app.test_client.post("/score", content=pullover_bytes, headers=custom_headers)
    _, resp2 = app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)
    # TODO: prove second request doesn't overwrite request 1's log_level
    assert resp1.status == 200
    assert resp1.body == b"Pullover"
    assert resp1.text == "Pullover"
    assert resp1.headers.get("content-type") == "text/plain; charset=utf-8"


def test_multiple_log_levels(app, basic_headers, pullover_bytes):
    basic_headers["x-ms-log-level"] = "critical"
    basic_headers["x-ms-log-level"] = "debug"
    _, resp1 = app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)
    assert resp1.status == 200
    assert resp1.body == b"Pullover"
    assert resp1.text == "Pullover"
    assert resp1.headers.get("content-type") == "text/plain; charset=utf-8"
