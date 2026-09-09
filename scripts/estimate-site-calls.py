from argparse import ArgumentParser
from pathlib import Path
import json
import math
import os
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auto_dev import server


def main():
    parser = ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    api_key = os.environ.get("AUTO_DEV_API_KEY")
    if not api_key:
        raise SystemExit("AUTO_DEV_API_KEY is not set.")

    config = json.loads(args.config.read_text(encoding="utf-8"))
    response = server.fetch_page(api_key, 1, config)
    items = list(response.get("data") or [])
    total = int(response.get("total") or len(items))
    page_size = len(items)
    calls = max(1, math.ceil(total / page_size)) if page_size else 1
    report = {
        "vehicleName": config["vehicleName"],
        "sourceResults": total,
        "pageSize": page_size,
        "callsPerUpdate": calls,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"{report['vehicleName']}: {total} source results, "
        f"{page_size} per page, {calls} calls per update."
    )


if __name__ == "__main__":
    main()
