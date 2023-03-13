import os
import pytest
import uuid


def test_request_without_request_id(app, pullover_bytes, basic_headers):
    _, resp = app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)

    assert resp.status == 200
    assert resp.body == b"Pullover"
    assert "x-ms-request-id" in resp.headers
    assert is_valid_uuid(resp.headers["x-ms-request-id"])


def test_request_with_request_id(app, pullover_bytes, basic_headers):
    req_id = "test_foo"
    basic_headers.update({"x-ms-request-id": req_id})

    _, resp = app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)

    assert resp.status == 200
    assert resp.body == b"Pullover"
    assert "x-ms-request-id" in resp.headers
    assert resp.headers["x-ms-request-id"] == req_id


def test_request_without_request_id_with_user_error(app, pullover_bytes, basic_headers):
    _, resp = app.test_client.post("/score1", content=pullover_bytes, headers=basic_headers)

    assert resp.status == 404
    assert "x-ms-request-id" in resp.headers
    assert is_valid_uuid(resp.headers["x-ms-request-id"])


def test_request_with_request_id_with_user_error(app, pullover_bytes, basic_headers):
    req_id = "test_foo"
    basic_headers.update({"x-ms-request-id": req_id})

    _, resp = app.test_client.post("/score1", content=pullover_bytes, headers=basic_headers)

    assert resp.status == 404
    assert "x-ms-request-id" in resp.headers
    assert resp.headers["x-ms-request-id"] == req_id


def test_request_without_request_id_with_server_error(app, pullover_bytes):
    # TODO: we need a better injection server error
    headers = {"something": "image/jpeg", "accept": "application/json"}

    _, resp = app.test_client.post("/score", content=pullover_bytes, headers=headers)

    assert resp.status == 500
    assert "x-ms-request-id" in resp.headers
    assert is_valid_uuid(resp.headers["x-ms-request-id"])


def test_request_with_request_id_with_server_error(app, pullover_bytes):
    req_id = "test_foo"
    headers = {
        "something": "image/jpeg",
        "accept": "application/json",
        "x-ms-request-id": req_id,
    }

    _, resp = app.test_client.post("/score", content=pullover_bytes, headers=headers)

    assert resp.status == 500
    assert "x-ms-request-id" in resp.headers
    assert resp.headers["x-ms-request-id"] == req_id


def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False
