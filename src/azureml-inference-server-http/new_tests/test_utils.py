import os
import pathlib

import pytest

from azureml_inference_server_http.server.utils import walk_path


def test_utils_walk_path(tmp_path: pathlib.Path):
    # fmt: off
    filepaths = [
        tmp_path / "dir" / "file1",
        tmp_path / "dir" / "file2",
        tmp_path / "file",
    ]
    # fmt: on

    # Create the filepaths
    for filepath in filepaths:
        # Ensure the parent directory exists before trying to create the file
        filepath.parent.mkdir(parents=True, exist_ok=True)
        # Create the file itself
        filepath.touch()

    generator = walk_path(tmp_path)

    # Root directory should come first
    assert next(generator) == f"{os.path.basename(tmp_path)}{os.sep}"

    # Directories walk before files
    assert next(generator) == f"    dir{os.sep}"

    # Files at the maximum depth
    assert next(generator) == "        file1"
    assert next(generator) == "        file2"

    # Files in the root once we are out of directories
    assert next(generator) == "    file"

    with pytest.raises(StopIteration):
        next(generator)
