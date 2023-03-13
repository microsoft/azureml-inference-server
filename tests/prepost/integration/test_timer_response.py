def test_timer_header_in_response(app, pullover_bytes, basic_headers):
    _, resp = app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)

    assert resp.status == 200
    assert resp.body == b"Pullover"
    assert "x-ms-infr-exec-ms" in resp.headers
    assert "x-ms-preproc-exec-ms" in resp.headers
    assert "x-ms-postproc-exec-ms" in resp.headers
    assert float(resp.headers["x-ms-infr-exec-ms"]) > 0
    assert float(resp.headers["x-ms-preproc-exec-ms"]) > 0
    assert float(resp.headers["x-ms-postproc-exec-ms"]) > 0
