from pathlib import Path
import sys
ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = ROOT / 'scripts'
sys.path.append(str(SCRIPTS_DIR))

import sqlite3
import pytest

from setup import create_tables


@pytest.fixture
def conn():
    """In memory sqlite database for testing"""
    _conn = sqlite3.connect(":memory:")
    create_tables(_conn)
    yield _conn
    _conn.close()

