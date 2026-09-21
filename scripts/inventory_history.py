from datetime import date as calendar_date, timedelta
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
HISTORY_FILE = ROOT / "vehicles" / "bmw-ix" / "inventory-history.json"
SNAPSHOT_FILE = ROOT / "vehicles" / "bmw-ix" / "inventory.json"
RETENTION_DAYS = 7


def empty_history():
    return {
        "retentionDays": RETENTION_DAYS,
        "updatedAt": None,
        "snapshots": [],
        "vehicles": {},
    }


def update_history(history, snapshot):
    snapshot_date = snapshot.get("lastRefreshDate")
    if not snapshot_date:
        raise ValueError("A successful snapshot date is required for history.")

    cutoff = (
        calendar_date.fromisoformat(snapshot_date) - timedelta(days=RETENTION_DAYS - 1)
    ).isoformat()
    value = {**empty_history(), **(history or {})}
    snapshots = [
        item
        for item in value.get("snapshots", [])
        if cutoff <= item.get("date", "") <= snapshot_date
        and item.get("date") != snapshot_date
    ]
    listings = {
        listing["vin"]: listing
        for listing in snapshot.get("listings", [])
        if listing.get("vin")
    }
    snapshots.append({"date": snapshot_date, "vins": sorted(listings)})
    snapshots.sort(key=lambda item: item["date"])

    vehicles = dict(value.get("vehicles") or {})
    for vin, listing in listings.items():
        vehicle = dict(vehicles.get(vin) or {})
        observations = [
            item
            for item in vehicle.get("observations", [])
            if cutoff <= item.get("date", "") <= snapshot_date
            and item.get("date") != snapshot_date
        ]
        observations.append(
            {
                "date": snapshot_date,
                "price": listing.get("price"),
                "mileage": listing.get("mileage"),
                "dealer": listing.get("dealer"),
            }
        )
        observations.sort(key=lambda item: item["date"])
        vehicles[vin] = {
            "lastKnown": {key: item for key, item in listing.items() if key != "isNew"},
            "observations": observations,
        }

    retained_vehicles = {}
    for vin, vehicle in vehicles.items():
        observations = [
            item
            for item in vehicle.get("observations", [])
            if cutoff <= item.get("date", "") <= snapshot_date
        ]
        if observations:
            retained_vehicles[vin] = {
                "lastKnown": vehicle.get("lastKnown", {}),
                "observations": observations,
            }

    return {
        "retentionDays": RETENTION_DAYS,
        "updatedAt": snapshot.get("updatedAt"),
        "snapshots": snapshots,
        "vehicles": retained_vehicles,
    }


def write_history(snapshot_file=SNAPSHOT_FILE, history_file=HISTORY_FILE):
    snapshot = json.loads(snapshot_file.read_text(encoding="utf-8"))
    try:
        history = json.loads(history_file.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        history = empty_history()
    updated = update_history(history, snapshot)
    temporary = history_file.with_suffix(".tmp")
    temporary.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    temporary.replace(history_file)
    return updated


if __name__ == "__main__":
    result = write_history()
    print(
        f"Recorded {len(result['vehicles'])} vehicles across "
        f"{len(result['snapshots'])} successful snapshots."
    )
