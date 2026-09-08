from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "auto-dev-cache.json"
DESTINATION = ROOT / "data" / "auto-dev-listings.json"
LISTING_FIELDS = {
    "id",
    "vin",
    "year",
    "make",
    "model",
    "trim",
    "price",
    "mileage",
    "exteriorColor",
    "interiorColor",
    "dealer",
    "officialBmwDealer",
    "city",
    "state",
    "zip",
    "cpo",
    "oneOwner",
    "accidentFree",
    "accidentCount",
    "usageType",
    "image",
    "photoCount",
    "url",
    "carfaxUrl",
    "listedAt",
    "isNew",
    "firstSeenDate",
}


def export_snapshot():
    cache = json.loads(SOURCE.read_text(encoding="utf-8"))
    listings = [
        {key: value for key, value in listing.items() if key in LISTING_FIELDS}
        for listing in cache.get("listings", [])
    ]
    snapshot = {
        "staticSnapshot": True,
        "updatedAt": cache.get("updatedAt"),
        "lastRefreshDate": cache.get("lastRefreshDate"),
        "lastAttemptCalls": cache.get("lastAttemptCalls", 0),
        "apiTotal": cache.get("apiTotal", len(listings)),
        "listingCount": len(listings),
        "newCount": cache.get("newCount", 0),
        "removedCount": cache.get("removedCount", 0),
        "listings": listings,
    }
    temporary = DESTINATION.with_suffix(".tmp")
    temporary.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    temporary.replace(DESTINATION)
    print(f"Exported {len(listings)} sanitized Auto.dev listings to {DESTINATION}")


if __name__ == "__main__":
    export_snapshot()
