from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
from urllib.error import URLError
import importlib.util
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_dev import server

exporter_spec = importlib.util.spec_from_file_location(
    "export_auto_dev_snapshot",
    Path(__file__).resolve().parent.parent / "scripts" / "export-auto-dev-snapshot.py",
)
exporter = importlib.util.module_from_spec(exporter_spec)
exporter_spec.loader.exec_module(exporter)


def listing(vin, dealer="BMW Seattle"):
    return {
        "vin": vin,
        "vehicle": {
            "vin": vin,
            "year": 2024,
            "make": "BMW",
            "model": "iX",
            "trim": "xDrive50",
            "exteriorColor": "Blue",
            "interiorColor": "Black",
        },
        "retailListing": {
            "dealer": dealer,
            "city": "Seattle",
            "state": "WA",
            "used": True,
            "price": 50000,
            "miles": 10000,
            "primaryImage": f"https://example.com/{vin}.jpg",
            "vdp": f"https://example.com/{vin}",
        },
        "history": {"oneOwner": True, "accidents": False, "usageType": "Personal Use"},
    }


class AutoDevCacheTests(TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.original_cache_file = server.CACHE_FILE
        self.original_overrides_file = server.OVERRIDES_FILE
        server.CACHE_FILE = Path(self.temporary.name) / "cache.json"
        server.OVERRIDES_FILE = Path(self.temporary.name) / "overrides.json"

    def tearDown(self):
        server.CACHE_FILE = self.original_cache_file
        server.OVERRIDES_FILE = self.original_overrides_file
        self.temporary.cleanup()

    def test_refresh_fetches_each_page_only_once_per_day(self):
        calls = []
        vins = [f"WB523CF0{i:09d}"[-17:] for i in range(45)]

        def fetcher(_key, page):
            calls.append(page)
            start = (page - 1) * 20
            return {"total": 45, "data": [listing(vin) for vin in vins[start:start + 20]]}

        first = server.refresh_cache(fetcher=fetcher, date="2026-09-07", api_key="test")
        same_day = server.refresh_cache(fetcher=fetcher, date="2026-09-07", api_key="test")

        self.assertEqual(calls, [1, 2, 3])
        self.assertEqual(first["listingCount"], 45)
        self.assertEqual(first["newCount"], 0)
        self.assertEqual(same_day["lastAttemptCalls"], 3)

    def test_refresh_stops_before_exceeding_call_limit(self):
        calls = []

        def fetcher(_key, page):
            calls.append(page)
            return {"total": 101, "data": [listing("WB523CF0000000001") for _ in range(20)]}

        cache = server.refresh_cache(
            fetcher=fetcher,
            date="2026-09-07",
            api_key="test",
            max_calls=5,
        )

        self.assertEqual(calls, [1])
        self.assertEqual(cache["lastAttemptCalls"], 1)
        self.assertIn("configured maximum is 5", cache["refreshError"])

    def test_next_day_marks_only_unseen_vins_new(self):
        first_vins = ["WB523CF0000000001", "WB523CF0000000002"]
        next_vins = ["WB523CF0000000002", "WB523CF0000000003"]
        current = first_vins

        def fetcher(_key, _page):
            return {"total": len(current), "data": [listing(vin) for vin in current]}

        server.refresh_cache(fetcher=fetcher, date="2026-09-07", api_key="test")
        current = next_vins
        refreshed = server.refresh_cache(fetcher=fetcher, date="2026-09-08", api_key="test")

        self.assertEqual(refreshed["newCount"], 1)
        self.assertEqual(refreshed["removedCount"], 1)
        new_listing = next(item for item in refreshed["listings"] if item["isNew"])
        self.assertEqual(new_listing["vin"], "WB523CF0000000003")

    def test_older_date_cannot_replace_newer_attempt_marker(self):
        calls = []

        def fetcher(_key, page):
            calls.append(page)
            return {"total": 1, "data": [listing("WB523CF0000000001")]}

        server.refresh_cache(fetcher=fetcher, date="2026-09-08", api_key="test")
        cache = server.refresh_cache(fetcher=fetcher, date="2026-09-07", api_key="test")

        self.assertEqual(calls, [1])
        self.assertEqual(cache["lastAttemptDate"], "2026-09-08")

    def test_failed_next_day_refresh_clears_old_new_markers(self):
        current = ["WB523CF0000000001"]

        def fetcher(_key, _page):
            return {"total": len(current), "data": [listing(vin) for vin in current]}

        server.refresh_cache(fetcher=fetcher, date="2026-09-07", api_key="test")
        current.append("WB523CF0000000002")
        server.refresh_cache(fetcher=fetcher, date="2026-09-08", api_key="test")

        def failing_fetcher(_key, _page):
            raise URLError("offline")

        failed = server.refresh_cache(fetcher=failing_fetcher, date="2026-09-09", api_key="test")

        self.assertEqual(failed["newCount"], 0)
        self.assertEqual(failed["removedCount"], 0)
        self.assertFalse(any(item["isNew"] for item in failed["listings"]))
        self.assertIn("Could not reach Auto.dev", failed["refreshError"])

    def test_dealer_names_differing_only_by_case_are_collapsed(self):
        items = [
            listing("WB523CF0000000001", dealer="bmw northwest"),
            listing("WB523CF0000000002", dealer="BMW Northwest"),
        ]

        def fetcher(_key, _page):
            return {"total": len(items), "data": items}

        cache = server.refresh_cache(fetcher=fetcher, date="2026-09-07", api_key="test")

        self.assertEqual({item["dealer"] for item in cache["listings"]}, {"BMW Northwest"})
        self.assertTrue(all(item["officialBmwDealer"] for item in cache["listings"]))

    def test_known_independent_dealer_uses_canonical_name(self):
        items = [listing("WB523CF0000000001", dealer="jaguar land rover bellevue")]

        def fetcher(_key, _page):
            return {"total": 1, "data": items}

        cache = server.refresh_cache(fetcher=fetcher, date="2026-09-07", api_key="test")

        self.assertEqual(cache["listings"][0]["dealer"], "Jaguar Land Rover Bellevue")
        self.assertFalse(cache["listings"][0]["officialBmwDealer"])

    def test_verified_listing_override_reconciles_cpo_and_dealer_url(self):
        vin = "WB523CF0000000001"
        server.OVERRIDES_FILE.write_text(
            '{"WB523CF0000000001":{"cpo":true,"url":"https://dealer.example/vehicle"}}',
            encoding="utf-8",
        )

        def fetcher(_key, _page):
            return {"total": 1, "data": [listing(vin)]}

        cache = server.refresh_cache(fetcher=fetcher, date="2026-09-07", api_key="test")
        corrected = cache["listings"][0]

        self.assertTrue(corrected["cpo"])
        self.assertEqual(corrected["url"], "https://dealer.example/vehicle")

    def test_snapshot_override_rejects_unapproved_fields_and_insecure_url(self):
        original = {"vin": "WB523CF0000000001", "price": 50000, "cpo": False, "url": "https://dealer.example"}
        override = {"vin": "ALTERED", "price": 1, "cpo": True, "url": "http://insecure.example"}

        corrected = exporter.apply_override(original, override)

        self.assertEqual(corrected["vin"], original["vin"])
        self.assertEqual(corrected["price"], original["price"])
        self.assertTrue(corrected["cpo"])
        self.assertEqual(corrected["url"], original["url"])

    def test_verified_null_url_override_suppresses_stale_dealer_link(self):
        original = {"vin": "WB523CF0000000001", "url": "https://dealer.example/stale"}

        corrected = exporter.apply_override(original, {"url": None})

        self.assertIsNone(corrected["url"])


if __name__ == "__main__":
    main()
