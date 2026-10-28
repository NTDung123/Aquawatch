"""Use ordinary project-local directories on restricted Windows accounts."""
from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture
def tmp_path():
    # Python's private 0700 temp ACL excludes the sandbox token on this machine.
    directory = Path(__file__).resolve().parents[1] / ".work" / "test_artifacts" / uuid4().hex
    directory.mkdir(parents=True, mode=0o777)
    return directory
