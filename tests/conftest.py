import importlib

import pytest


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the app at an empty temporary SQLite database."""
    monkeypatch.setenv("ROADSENSE_DB", str(tmp_path / "test.db"))
    import src.database as database

    importlib.reload(database)
    database.init_db()
    yield database
    monkeypatch.delenv("ROADSENSE_DB")
    importlib.reload(database)
