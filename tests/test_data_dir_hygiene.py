from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


def _cleanup_test_sqlite_artifacts_in_data_dir() -> None:
    if not DATA_DIR.exists():
        return
    for path in DATA_DIR.iterdir():
        if path.name.startswith("test_"):
            try:
                path.unlink()
            except OSError:
                pass


def test_data_dir_has_no_pytest_sqlite_artifacts():
    _cleanup_test_sqlite_artifacts_in_data_dir()
    if not DATA_DIR.exists():
        return

    offenders = [path.name for path in DATA_DIR.iterdir() if path.name.startswith("test_")]
    assert offenders == [], f"unexpected test sqlite artifacts in data/: {offenders}"
