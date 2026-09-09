from datetime import datetime
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

exporter_spec = importlib.util.spec_from_file_location(
    "export_auto_dev_snapshot",
    ROOT / "scripts" / "export-auto-dev-snapshot.py",
)
exporter = importlib.util.module_from_spec(exporter_spec)
exporter_spec.loader.exec_module(exporter)

REPOSITORIES = [
    "wa-ix-finder",
    "wa-model-x-finder",
    "wa-model-y-finder",
    "wa-sienna-finder",
    "wa-ex90-finder",
    "wa-id-buzz-finder",
    "wa-eqe-suv-finder",
    "wa-eqs-suv-finder",
]


def main():
    api_key = os.environ.get("AUTO_DEV_API_KEY")
    portfolio = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    date = datetime.now().astimezone().date().isoformat()
    if not api_key:
        raise SystemExit("AUTO_DEV_API_KEY is not set.")

    originals = {
        "cache": server.CACHE_FILE,
        "overrides": server.OVERRIDES_FILE,
        "config": server.SITE_CONFIG_FILE,
        "source": exporter.SOURCE,
        "destination": exporter.DESTINATION,
    }
    try:
        for repository in REPOSITORIES:
            repository_root = ROOT if repository == "wa-ix-finder" else portfolio / repository
            snapshot_file = repository_root / "data" / "inventory.json"
            state_file = repository_root / "data" / "refresh-state.json"
            cache_file = output / repository / "auto-dev-cache.json"
            destination = output / repository / "inventory.json"
            state = refresh.read_json(state_file, {})
            snapshot = refresh.read_json(snapshot_file, {})

            server.CACHE_FILE = cache_file
            server.OVERRIDES_FILE = repository_root / "data" / "listing-overrides.json"
            server.SITE_CONFIG_FILE = repository_root / "data" / "site-config.json"
            refresh.write_json(cache_file, refresh.cache_from_snapshot(snapshot, state))
            config = server.read_site_config()
            refreshed = server.refresh_cache(
                date=date,
                api_key=api_key,
                max_calls=config["maxApiCalls"],
            )
            if refreshed.get("refreshError"):
                raise RuntimeError(f"{repository}: {refreshed['refreshError']}")

            exporter.SOURCE = cache_file
            exporter.DESTINATION = destination
            exporter.OVERRIDES = server.OVERRIDES_FILE
            exporter.export_snapshot()
            shutil.copy2(server.SITE_CONFIG_FILE, output / repository / "site-config.json")
            print(
                f"{repository}: {refreshed['listingCount']} listings, "
                f"{refreshed['lastAttemptCalls']} calls"
            )
    finally:
        server.CACHE_FILE = originals["cache"]
        server.OVERRIDES_FILE = originals["overrides"]
        server.SITE_CONFIG_FILE = originals["config"]
        exporter.SOURCE = originals["source"]
        exporter.DESTINATION = originals["destination"]


if __name__ == "__main__":
    main()
