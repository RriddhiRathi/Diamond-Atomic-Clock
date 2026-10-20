"""Keep regression runs independent of a developer's persistent bibliography."""
import pytest


@pytest.fixture(autouse=True)
def isolated_reference_database(tmp_path, monkeypatch):
    monkeypatch.setenv("DIAMONDCLOCK_REFERENCE_DB", str(tmp_path / "references.sqlite3"))
