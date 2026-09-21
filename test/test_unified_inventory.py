from pathlib import Path
from unittest import TestCase, main
import json

ROOT = Path(__file__).resolve().parent.parent


class UnifiedInventoryTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(
            (ROOT / "data" / "vehicles.json").read_text(encoding="utf-8")
        )

    def test_default_and_vehicle_slugs_are_valid(self):
        slugs = [vehicle["slug"] for vehicle in self.config["vehicles"]]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertIn(self.config["defaultVehicle"], slugs)
        self.assertEqual(
            set(slugs),
            {path.name for path in (ROOT / "vehicles").iterdir() if path.is_dir()},
        )

    def test_every_vehicle_has_valid_refresh_configuration(self):
        for vehicle in self.config["vehicles"]:
            with self.subTest(vehicle=vehicle["slug"]):
                refresh = vehicle["refresh"]
                self.assertIsInstance(refresh["enabled"], bool)
                self.assertGreaterEqual(refresh["intervalDays"], 1)
                self.assertNotIn("maxApiCalls", refresh)

    def test_snapshots_and_histories_match_vehicle_configuration(self):
        for vehicle in self.config["vehicles"]:
            with self.subTest(vehicle=vehicle["slug"]):
                directory = ROOT / "vehicles" / vehicle["slug"]
                inventory = json.loads(
                    (directory / "inventory.json").read_text(encoding="utf-8")
                )
                history = json.loads(
                    (directory / "inventory-history.json").read_text(encoding="utf-8")
                )
                listings = inventory["listings"]
                self.assertEqual(inventory["listingCount"], len(listings))
                self.assertGreater(len(listings), 0)
                self.assertTrue(
                    all(
                        listing["make"] == vehicle["make"]
                        and listing["model"] == vehicle["model"]
                        and listing["state"] == "WA"
                        and listing["year"] >= vehicle["minimumYear"]
                        for listing in listings
                    )
                )
                self.assertEqual(
                    history["snapshots"][-1]["date"],
                    inventory["lastRefreshDate"],
                )
                self.assertEqual(
                    set(history["snapshots"][-1]["vins"]),
                    {listing["vin"] for listing in listings},
                )


if __name__ == "__main__":
    main()
