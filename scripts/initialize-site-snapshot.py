from argparse import ArgumentParser
from pathlib import Path
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

refresh_spec = importlib.util.spec_from_file_location(
    "refresh_published_inventory",
    ROOT / "scripts" / "refresh-published-inventory.py",
)
refresh = importlib.util.module_from_spec(refresh_spec)
refresh_spec.loader.exec_module(refresh)


def main():
    parser = ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    shutil.copyfile(args.config, refresh.server.SITE_CONFIG_FILE)
    refresh.server.OVERRIDES_FILE.write_text("{}\n", encoding="utf-8")
    refresh.write_json(
        refresh.SNAPSHOT_FILE,
        {
            "publishedSnapshot": True,
            "updatedAt": None,
            "lastRefreshDate": None,
            "lastAttemptCalls": 0,
            "apiTotal": 0,
            "listingCount": 0,
            "newCount": 0,
            "removedCount": 0,
            "listings": [],
        },
    )
    refresh.write_json(refresh.STATE_FILE, {})
    refresh.reserve_refresh(args.date)
    if not refresh.refresh_snapshot(args.date, None):
        raise SystemExit(1)

    state = json.loads(refresh.STATE_FILE.read_text(encoding="utf-8"))
    print(
        f"Initial snapshot complete: {state['lastAttemptCalls']} calls on "
        f"{state['lastSuccessfulRefreshDate']}."
    )


if __name__ == "__main__":
    main()
