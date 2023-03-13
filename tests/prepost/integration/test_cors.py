def test_preflight_post_score(app, basic_headers):
    basic_headers.update({"Access-Control-Request-Method": "POST"})

    _, resp = app.test_client.options("/score", headers=basic_headers)

    assert resp.status == 200
    assert resp.content == b""
    assert "access-control-allow-origin" in resp.headers
    assert resp.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-methods" in resp.headers
    assert resp.headers["access-control-allow-methods"] == "OPTIONS, POST"


def test_post_request_cors(app, pullover_bytes, basic_headers):
    _, resp = app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)

    assert resp.status == 200
    assert resp.content == b"Pullover"
    assert "x-ms-request-id" in resp.headers
    assert "access-control-allow-origin" in resp.headers
    assert resp.headers["access-control-allow-origin"] == "*"


def test_post_request_cors_with_origin(app, pullover_bytes, basic_headers):
    basic_headers.update({"Origin": "hello.world"})
    _, resp = app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)

    assert resp.status == 200
    assert resp.content == b"Pullover"
    assert "x-ms-request-id" in resp.headers
    assert "access-control-allow-origin" in resp.headers
    assert resp.headers["access-control-allow-origin"] == "hello.world"
    assert "vary" in resp.headers
    assert resp.headers["vary"] == "Origin"
