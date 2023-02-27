import pytest


def test_skip_inference(app, basic_headers, pullover_bytes):
    basic_headers["x-ms-custom"] = "skip-inference"
    _, resp = app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)
    assert resp.status == 200
    assert resp.body == b"inference_skipped"
    assert resp.text == "inference_skipped"
    assert resp.headers.get("content-type") == "text/plain; charset=utf-8"


def test_skip_inference_removed(app, basic_headers, pullover_bytes):
    basic_headers["x-ms-custom"] = "remove-skip-inference"
    _, resp = app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)
    assert resp.status == 200
    assert resp.body == b"Pullover"
    assert resp.text == "Pullover"
    assert resp.headers.get("content-type") == "text/plain; charset=utf-8"


def test_skip_inference_mangled(app, basic_headers, pullover_bytes):
    basic_headers["x-ms-custom"] = "mangle-skip-inference"
    _, resp = app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)
    assert resp.status == 200
    assert resp.body == b"Pullover"
    assert resp.text == "Pullover"
    assert resp.headers.get("content-type") == "text/plain; charset=utf-8"
