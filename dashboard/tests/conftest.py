import sys
from pathlib import Path

import pytest

DASHBOARD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DASHBOARD))

FIXTURES = Path(__file__).resolve().parent / "fixtures"

from storage import HistoryStore  # noqa: E402


@pytest.fixture
def store(tmp_path):
    return HistoryStore(tmp_path / "history.db", tmp_path / "artifacts")


@pytest.fixture
def fixtures():
    return FIXTURES
