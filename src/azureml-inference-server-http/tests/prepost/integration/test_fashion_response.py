import pytest


def test_basic_asgi_client(app):
    _, response = app.test_client.get("/")
    assert response.text == '{"Status":"OK. Ready to serve requests."}'
    assert response.status == 200
    assert response.headers.get("content-type") == "application/json"


def test_image_request(app, basic_headers, pullover_bytes):
    _, resp = app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)
    assert resp.status == 200
    assert resp.body == b"Pullover"
    assert resp.text == "Pullover"
    assert resp.headers.get("content-type") == "text/plain; charset=utf-8"


def test_image_json_response(app, basic_headers, pullover_bytes):
    basic_headers["accept"] = "application/json"
    _, resp = app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)
    assert resp.status == 200
    assert resp.json == "Pullover"
    assert resp.headers.get("content-type") == "application/json"


def test_image_raw_response(app, basic_headers, pullover_bytes):
    basic_headers["accept"] = "application/octet-stream"
    _, resp = app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)
    assert resp.status == 200
    assert resp.body == b"Pullover"
    assert resp.headers.get("content-type") == "application/octet-stream"


def test_throws_error(app, basic_headers, pullover_bytes):
    # Script should throw exception if not image content
    basic_headers["content-type"] = "application/octet-stream"
    _, resp = app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)
    assert resp.status == 500
