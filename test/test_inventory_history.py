from datetime import date, timedelta
from unittest import TestCase, main

from scripts import inventory_history


def snapshot(day, listings):
    return {
        "lastRefreshDate": day,
        "updatedAt": f"{day}T09:17:00Z",
        "listings": listings,
    }


def listing(vin, price, mileage=10000):
    return {
        "vin": vin,
        "year": 2024,
        "model": "iX",
        "price": price,
        "mileage": mileage,
        "dealer": "BMW Seattle",
        "isNew": False,
    }


class InventoryHistoryTests(TestCase):
    def test_tracks_presence_price_changes_and_removals(self):
        history = inventory_history.update_history(
            None,
            snapshot("2026-09-19", [listing("VIN1", 50000), listing("VIN2", 60000)]),
        )
        history = inventory_history.update_history(
            history,
            snapshot("2026-09-20", [listing("VIN1", 48000)]),
        )

        self.assertEqual(len(history["snapshots"]), 2)
        self.assertEqual(
            [item["price"] for item in history["vehicles"]["VIN1"]["observations"]],
            [50000, 48000],
        )
        self.assertEqual(
            history["vehicles"]["VIN2"]["observations"][0]["date"],
            "2026-09-19",
        )

    def test_same_day_update_is_idempotent(self):
        history = inventory_history.update_history(
            None,
            snapshot("2026-09-20", [listing("VIN1", 50000)]),
        )
        history = inventory_history.update_history(
            history,
            snapshot("2026-09-20", [listing("VIN1", 49000)]),
        )

        self.assertEqual(len(history["snapshots"]), 1)
        self.assertEqual(
            history["vehicles"]["VIN1"]["observations"],
            [
                {
                    "date": "2026-09-20",
                    "price": 49000,
                    "mileage": 10000,
                    "dealer": "BMW Seattle",
                }
            ],
        )

    def test_prunes_observations_older_than_seven_days(self):
        start = date(2026, 9, 1)
        history = None
        for offset in range(10):
            day = (start + timedelta(days=offset)).isoformat()
            history = inventory_history.update_history(
                history,
                snapshot(day, [listing("VIN1", 50000 - offset)]),
            )

        self.assertEqual(len(history["snapshots"]), 7)
        self.assertEqual(history["snapshots"][0]["date"], "2026-09-04")
        self.assertEqual(
            history["vehicles"]["VIN1"]["observations"][0]["date"],
            "2026-09-04",
        )


if __name__ == "__main__":
    main()
