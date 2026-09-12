from pathlib import Path
import importlib.util
import json
import os
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auto_dev import server

refresh_spec = importlib.util.spec_from_file_location(
    "refresh_published_inventory",
    ROOT / "scripts" / "refresh-published-inventory.py",
)
refresh = importlib.util.module_from_spec(refresh_spec)
refresh_spec.loader.exec_module(refresh)

REPOSITORIES = [
    "wa-ex90-finder",
    "wa-id-buzz-finder",
    "wa-eqe-suv-finder",
    "wa-eqs-suv-finder",
]


def main():
    api_key = os.environ.get("AUTO_DEV_API_KEY")
    if not api_key:
        raise SystemExit("AUTO_DEV_API_KEY is not set.")

    portfolio = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    refresh_date = sys.argv[3]
    original_config = server.SITE_CONFIG_FILE
    original_overrides = server.OVERRIDES_FILE
    original_export_overrides = refresh.exporter.OVERRIDES
    try:
        for repository in REPOSITORIES:
            repository_root = portfolio / repository
            data_dir = repository_root / "data"
            state_file = data_dir / "refresh-state.json"
            snapshot_file = data_dir / "inventory.json"
            cache_file = output / repository / "auto-dev-cache.json"

            state = json.loads(state_file.read_text(encoding="utf-8"))
            state.update(
                {
                    "lastAttemptDate": refresh_date,
                    "lastAttemptCalls": 0,
                    "lastError": None,
                }
            )
            refresh.write_json(state_file, state)

            server.SITE_CONFIG_FILE = data_dir / "site-config.json"
            server.OVERRIDES_FILE = data_dir / "listing-overrides.json"
            refresh.exporter.OVERRIDES = server.OVERRIDES_FILE
            succeeded = refresh.refresh_snapshot(
                refresh_date,
                api_key,
                state_file=state_file,
                snapshot_file=snapshot_file,
                cache_file=cache_file,
            )
            if not succeeded:
                updated_state = json.loads(state_file.read_text(encoding="utf-8"))
                raise RuntimeError(f"{repository}: {updated_state.get('lastError')}")

            destination = output / repository / "data"
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copy2(snapshot_file, destination / "inventory.json")
            shutil.copy2(state_file, destination / "refresh-state.json")
    finally:
        server.SITE_CONFIG_FILE = original_config
        server.OVERRIDES_FILE = original_overrides
        refresh.exporter.OVERRIDES = original_export_overrides


if __name__ == "__main__":
    main()
