import logging


def test_print_log_redirect(app, caplog):
    with caplog.at_level(logging.INFO, logger="azmlinfsrv.print"):
        print("Informational Message")

    info_tuple = ("azmlinfsrv.print", logging.INFO, "Informational Message")
    assert info_tuple in caplog.record_tuples
