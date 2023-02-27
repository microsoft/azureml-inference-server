import uuid

import pytest


def assert_valid_guid(guid):
    try:
        uuid.UUID(guid)
    except ValueError:
        pytest.fail(f"{guid} is not a valid GUID.")
