from datetime import datetime
from pathlib import Path
import importlib.util
import json
import os
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auto_dev import server
from scripts import inventory_history

exporter_spec = importlib.util.spec_from_file_location(
    "export_auto_dev_snapshot",
    ROOT / "scripts" / "export-auto-dev-snapshot.py",
)
exporter = importlib.util.module_from_spec(exporter_spec)
exporter_spec.loader.exec_module(exporter)

SITES = {
    "wa-macan-electric-finder": {
        "siteTitle": "WA Macan Electric Finder",
        "vehicleName": "Porsche Macan Electric",
        "make": "Porsche",
        "model": "Macan",
        "minimumYear": 2022,
        "refreshIntervalDays": 2,
        "maxApiCalls": 2,
        "queryFuel": "Electric",
        "allowedPowertrains": ["Electric"],
        "brandMark": "ME",
        "fallbackImage": "assets/vehicle.svg",
        "dealerOnlyLabel": "Porsche dealers only",
        "dealerOnlyDescription": "Hide independent and other-brand dealers",
        "officialDealerNamePatterns": ["Porsche"],
        "dealerDomains": [
            "porsche.com",
            "porschebellevue.com",
            "porscheseattle.com",
            "porschespokane.com",
            "porschetacoma.com",
        ],
        "marketplaceDomains": ["autolist.com", "carvana.com"],
    },
    "wa-cayenne-electric-finder": {
        "siteTitle": "WA Cayenne Finder",
        "vehicleName": "Porsche Cayenne",
        "make": "Porsche",
        "model": "Cayenne",
        "minimumYear": 2022,
        "refreshIntervalDays": 2,
        "maxApiCalls": 10,
        "queryYearsSeparately": True,
        "brandMark": "CY",
        "fallbackImage": "assets/vehicle.svg",
        "dealerOnlyLabel": "Porsche dealers only",
        "dealerOnlyDescription": "Hide independent and other-brand dealers",
        "officialDealerNamePatterns": ["Porsche"],
        "dealerDomains": [
            "porsche.com",
            "porschebellevue.com",
            "porscheseattle.com",
            "porschespokane.com",
            "porschetacoma.com",
        ],
        "marketplaceDomains": ["autolist.com", "carvana.com"],
    },
    "wa-grecale-electric-finder": {
        "siteTitle": "WA Grecale Finder",
        "vehicleName": "Maserati Grecale",
        "make": "Maserati",
        "model": "Grecale",
        "minimumYear": 2022,
        "refreshIntervalDays": 2,
        "maxApiCalls": 2,
        "brandMark": "GR",
        "fallbackImage": "assets/vehicle.svg",
        "dealerOnlyLabel": "Maserati dealers only",
        "dealerOnlyDescription": "Hide independent and other-brand dealers",
        "officialDealerNamePatterns": ["Maserati"],
        "dealerDomains": [
            "maseratiofseattle.com",
            "maseratiofwashington.com",
        ],
        "marketplaceDomains": ["autolist.com", "carvana.com"],
    },
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main():
    api_key = os.environ.get("AUTO_DEV_API_KEY")
    output = Path(sys.argv[1]).resolve()
    refresh_date = sys.argv[2]
    if not api_key:
        raise SystemExit("AUTO_DEV_API_KEY is not set.")

    originals = (
        server.CACHE_FILE,
        server.OVERRIDES_FILE,
        server.SITE_CONFIG_FILE,
        exporter.SOURCE,
        exporter.DESTINATION,
        exporter.OVERRIDES,
    )
    try:
        for repository, config in SITES.items():
            data_dir = output / repository / "data"
            config_file = data_dir / "site-config.json"
            cache_file = data_dir / "auto-dev-cache.json"
            overrides_file = data_dir / "listing-overrides.json"
            snapshot_file = data_dir / "inventory.json"
            history_file = data_dir / "inventory-history.json"
            write_json(config_file, config)
            write_json(overrides_file, {})

            server.CACHE_FILE = cache_file
            server.OVERRIDES_FILE = overrides_file
            server.SITE_CONFIG_FILE = config_file
            refreshed = server.refresh_cache(
                date=refresh_date,
                api_key=api_key,
                max_calls=config["maxApiCalls"],
            )
            if refreshed.get("refreshError"):
                raise RuntimeError(f"{repository}: {refreshed['refreshError']}")

            exporter.SOURCE = cache_file
            exporter.DESTINATION = snapshot_file
            exporter.OVERRIDES = overrides_file
            exporter.export_snapshot()
            inventory_history.write_history(snapshot_file, history_file)
            write_json(
                data_dir / "refresh-state.json",
                {
                    "lastAttemptDate": refresh_date,
                    "lastSuccessfulRefreshDate": refresh_date,
                    "lastAttemptCalls": refreshed["lastAttemptCalls"],
                    "lastError": None,
                    "knownVins": refreshed.get("knownVins", {}),
                },
            )
            print(
                f"{repository}: {refreshed['listingCount']} listings, "
                f"{refreshed['lastAttemptCalls']} calls"
            )
    finally:
        (
            server.CACHE_FILE,
            server.OVERRIDES_FILE,
            server.SITE_CONFIG_FILE,
            exporter.SOURCE,
            exporter.DESTINATION,
            exporter.OVERRIDES,
        ) = originals


if __name__ == "__main__":
    main()
