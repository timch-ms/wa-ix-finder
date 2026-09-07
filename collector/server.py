from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import json
import os
import re
import threading

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "listings.json"
COLLECTED_FILE = ROOT / "data" / "collected.json"
PORT = int(os.environ.get("PORT", "4173"))
LOCKED_FIELDS = {"dealer", "city"}
COLLECTION_LOCK = threading.Lock()
MATERIAL_PATTERN = re.compile(r"\b(leather|merino|vernasca|nappa|sensatec|alcantara|wool|cloth)\b", re.IGNORECASE)
INVALID_COLOR_PATTERN = re.compile(r"^(not listed|color|location|360|360°|ext\.?|int\.?)$", re.IGNORECASE)
TRIM_PATTERN = re.compile(r"\b(xDrive(?:40|45|50|60)|M60|M70)\b", re.IGNORECASE)


def read_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def clean_listing(item, dealer, city):
    title = f"{item.get('year', '')} {item.get('make', '')} {item.get('model', '')}"
    if not re.search(r"\bBMW\s+iX\b", title, re.IGNORECASE):
        return None
    try:
        year = int(float(str(item["year"]).replace(",", "")))
        price = int(float(str(item["price"]).replace(",", "")))
        mileage = int(float(str(item["mileage"]).replace(",", "")))
    except (KeyError, TypeError, ValueError):
        return None
    if not 2022 <= year <= 2030 or not 10_000 <= price <= 200_000 or not 0 <= mileage <= 200_000:
        return None

    url = str(item.get("url", ""))
    if urlparse(url).scheme != "https":
        return None
    vin = str(item.get("vin") or "").upper() or None
    identifier = vin.lower() if vin else re.sub(r"[^a-z0-9]+", "-", url.lower()).strip("-")[-90:]
    exterior_color = str(item.get("exteriorColor") or "Not listed").strip()
    if INVALID_COLOR_PATTERN.match(exterior_color):
        exterior_color = "Not listed"
    interior_material = str(item.get("interiorMaterial") or "Not listed").strip()
    if not MATERIAL_PATTERN.search(interior_material):
        interior_material = "Not listed"
    return {
        "id": identifier,
        "year": year,
        "make": "BMW",
        "model": "iX",
        "trim": str(item.get("trim") or "Trim not listed")[:60],
        "price": price,
        "mileage": mileage,
        "exteriorColor": exterior_color[:80],
        "interiorMaterial": interior_material[:100],
        "dapp": item.get("dapp") is True,
        "dappEvidence": str(item.get("dappEvidence") or "Package not confirmed on rendered page")[:300],
        "dealer": dealer,
        "city": city,
        "url": url,
        "image": str(item.get("image") or "assets/ix-blue.svg"),
        "vin": vin,
        "verifiedAt": datetime.now(timezone.utc).date().isoformat(),
    }


def combined_inventory():
    baseline = read_json(DATA_FILE, {"listings": [], "sources": []})
    collected = read_json(COLLECTED_FILE, {"dealers": {}})
    listings = list(baseline.get("listings", []))
    sources = list(baseline.get("sources", []))
    configured_dealers = {source["name"] for source in sources}

    for dealer, result in collected.get("dealers", {}).items():
        if dealer not in configured_dealers:
            continue
        browser_listings = result.get("listings", [])
        if browser_listings or result.get("emptyConfirmed"):
            listings = [item for item in listings if item.get("dealer") != dealer]
            listings.extend(browser_listings)
        for source in sources:
            if source["name"] == dealer:
                source["status"] = result.get("status", "available")
                count = len(browser_listings)
                source["note"] = (
                    f"Browser collector scanned the rendered dealer page and found {count} matching "
                    f"vehicle{'s' if count != 1 else ''}."
                )

    unique = {}
    for item in listings:
        item = dict(item)
        color = str(item.get("exteriorColor") or "Not listed").strip()
        material = str(item.get("interiorMaterial") or "Not listed").strip()
        item["exteriorColor"] = "Not listed" if INVALID_COLOR_PATTERN.match(color) else color
        item["interiorMaterial"] = material if MATERIAL_PATTERN.search(material) else "Not listed"
        trim_match = TRIM_PATTERN.search(str(item.get("trim") or ""))
        if trim_match:
            item["trim"] = trim_match.group(1)
        key = item.get("vin") or item.get("id") or item.get("url")
        existing = unique.get(key)
        if not existing or item.get("dapp") or item.get("image", "").startswith("http"):
            unique[key] = item
    return {
        "updatedAt": collected.get("updatedAt") or baseline.get("updatedAt"),
        "listings": list(unique.values()),
        "sources": sources,
    }


class CollectorHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format_string, *args):
        print(f"[collector] {format_string % args}")

    def send_json(self, value, status=200):
        payload = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        if urlparse(self.path).path == "/api/inventory":
            self.send_json(combined_inventory())
            return
        super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/collect":
            self.send_json({"error": "Not found"}, 404)
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 2_000_000)
            body = json.loads(self.rfile.read(length))
            dealer = str(body["dealer"])[:80]
            city = str(body["city"])[:80]
            configured_dealers = {
                source["name"] for source in read_json(DATA_FILE, {"sources": []}).get("sources", [])
            }
            if dealer not in configured_dealers:
                self.send_json({"error": f"{dealer} is not a configured dealer"}, 400)
                return
            status = "blocked" if body.get("blocked") else "available"
            incoming = [
                listing for item in body.get("listings", [])
                if (listing := clean_listing(item, dealer, city)) is not None
            ]
            with COLLECTION_LOCK:
                current = read_json(COLLECTED_FILE, {"dealers": {}})
                previous = current["dealers"].get(dealer, {"listings": []})
                merged = {item.get("vin") or item["url"]: item for item in previous.get("listings", [])}
                for item in incoming:
                    key = item.get("vin") or item["url"]
                    old = merged.get(key, {})
                    old_color = old.get("exteriorColor")
                    old_material = old.get("interiorMaterial")
                    if item["exteriorColor"] == "Not listed" and old_color and old_color != "Not listed":
                        item["exteriorColor"] = old_color
                    if item["interiorMaterial"] == "Not listed" and old_material and old_material != "Not listed":
                        item["interiorMaterial"] = old_material
                    merged[key] = {**old, **item}
                    if old.get("dapp"):
                        merged[key]["dapp"] = True
                        merged[key]["dappEvidence"] = old["dappEvidence"]

                current["dealers"][dealer] = {
                    "status": status,
                    "url": body.get("pageUrl"),
                    "scannedAt": datetime.now(timezone.utc).isoformat(),
                    "emptyConfirmed": bool(body.get("emptyConfirmed")),
                    "listings": list(merged.values()),
                }
                current["updatedAt"] = datetime.now(timezone.utc).isoformat()
                write_json(COLLECTED_FILE, current)
            self.send_json({"ok": True, "accepted": len(incoming), "total": len(merged)})
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            print(f"[collector] rejected payload: {type(error).__name__}: {error}")
            self.send_json({"error": str(error)}, 400)


if __name__ == "__main__":
    print(f"WA iX Finder with Edge collector: http://127.0.0.1:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), CollectorHandler).serve_forever()
