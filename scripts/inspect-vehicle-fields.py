from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auto_dev import server


def matching_fields(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if any(token in key.casefold() for token in ("seat", "drive", "wheel")):
                yield child_path, child
            yield from matching_fields(child, child_path)
    elif isinstance(value, list):
        for child in value:
            yield from matching_fields(child, path)


def main():
    api_key = os.environ.get("AUTO_DEV_API_KEY")
    if not api_key:
        raise SystemExit("AUTO_DEV_API_KEY is not set.")
    config = server.read_site_config()
    response = server.fetch_page(api_key, 1, config)
    found = {}
    for item in response.get("data") or []:
        for path, value in matching_fields(item):
            found.setdefault(path, set()).add(json.dumps(value, sort_keys=True))
    for path, values in sorted(found.items()):
        print(f"{path}: {', '.join(sorted(values))}")


if __name__ == "__main__":
    main()
