import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auto_dev import server

QUERIES = [
    ("cayenne-all-powertrains", {"make": "Porsche", "model": "Cayenne"}),
    ("grecale-all-powertrains", {"make": "Maserati", "model": "Grecale"}),
]


def main():
    api_key = os.environ.get("AUTO_DEV_API_KEY")
    if not api_key:
        raise SystemExit("AUTO_DEV_API_KEY is not set.")
    for label, query in QUERIES:
        response = server.fetch_page(api_key, 1, query)
        rows = response.get("data") or []
        values = sorted(
            {
                (
                    str((row.get("vehicle") or {}).get("model")),
                    str((row.get("vehicle") or {}).get("trim")),
                    str((row.get("vehicle") or {}).get("fuel")),
                )
                for row in rows
            }
        )
        print(f"{label}: total={response.get('total', len(rows))}; values={values}")


if __name__ == "__main__":
    main()
