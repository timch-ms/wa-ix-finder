from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime
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
    parser.add_argument("--yearly", action="store_true")
    args = parser.parse_args()

    api_key = os.environ.get("AUTO_DEV_API_KEY")
    if not api_key:
        raise SystemExit("AUTO_DEV_API_KEY is not set.")

    config = json.loads(args.config.read_text(encoding="utf-8"))
    queries = []
    if args.yearly:
        years = range(config["minimumYear"], datetime.now().year + 2)
        queries = [{**config, "year": year} for year in years]
    else:
        queries = [config]

    totals = []
    for query_config in queries:
        response = server.fetch_page(api_key, 1, query_config)
        items = list(response.get("data") or [])
        total = int(response.get("total") or len(items))
        page_size = len(items)
        calls = max(1, math.ceil(total / page_size)) if page_size else 1
        totals.append(
            {
                "year": query_config.get("year"),
                "sourceResults": total,
                "pageSize": page_size,
                "callsPerUpdate": calls,
            }
        )

    report = {
        "vehicleName": config["vehicleName"],
        "sourceResults": sum(item["sourceResults"] for item in totals),
        "callsPerUpdate": sum(item["callsPerUpdate"] for item in totals),
        "queries": totals,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"{report['vehicleName']}: {report['sourceResults']} source results, "
        f"{report['callsPerUpdate']} calls per update."
    )


if __name__ == "__main__":
    main()
