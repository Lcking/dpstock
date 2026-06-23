from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_conftest_provides_isolated_db_fixture():
    conftest = (REPO_ROOT / "tests/conftest.py").read_text(encoding="utf-8")
    assert "def isolated_db" in conftest
    assert "INTEGRATION_MIGRATIONS" in conftest
    assert "def isolate_default_db_path" in conftest


def test_gitignore_blocks_test_db_artifacts_in_data_dir():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/test_*.db*" in gitignore
    assert "data/*.db-shm" in gitignore
    assert "data/*.db-wal" in gitignore
