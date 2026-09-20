from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import inventory_history


def committed_snapshots():
    result = subprocess.run(
        ["git", "log", "--format=%H", "--", "data/inventory.json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    for commit in result.stdout.splitlines():
        shown = subprocess.run(
            ["git", "show", f"{commit}:data/inventory.json"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if shown.returncode == 0:
            try:
                yield json.loads(shown.stdout)
            except json.JSONDecodeError:
                continue


def main():
    current = json.loads(inventory_history.SNAPSHOT_FILE.read_text(encoding="utf-8"))
    by_date = {
        snapshot["lastRefreshDate"]: snapshot
        for snapshot in [current, *committed_snapshots()]
        if snapshot.get("lastRefreshDate")
    }
    history = None
    for snapshot_date in sorted(by_date):
        history = inventory_history.update_history(history, by_date[snapshot_date])
    inventory_history.HISTORY_FILE.write_text(
        json.dumps(history, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Rebuilt {len(history['snapshots'])} snapshots with "
        f"{len(history['vehicles'])} vehicles."
    )


if __name__ == "__main__":
    main()
