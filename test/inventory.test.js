import test from "node:test";
import assert from "node:assert/strict";
import { normalizeMaterial, sortListings, uniqueValues } from "../lib/inventory.js";
import { listingDestination, listingHistoryInfo } from "../lib/inventory-view-v2.js";

test("classifies genuine leather without mislabeling Sensatec", () => {
  assert.equal(normalizeMaterial("Amido Perforated Full Merino Leather"), "Genuine leather");
  assert.equal(normalizeMaterial("Oyster Perforated Sensatec"), "Sensatec / synthetic");
  assert.equal(normalizeMaterial("Not listed"), "Not listed");
});

test("sorts listings without mutating the source", () => {
  const source = [{ year: 2024, price: 50, mileage: 9 }, { year: 2026, price: 80, mileage: 2 }];
  assert.equal(sortListings(source, "mileage-asc")[0].year, 2026);
  assert.equal(source[0].year, 2024);
});

test("returns unique descending years", () => {
  assert.deepEqual(uniqueValues([{ year: 2024 }, { year: 2026 }, { year: 2024 }], (x) => x.year), [2026, 2024]);
});

test("derives prior availability and price change from history", () => {
  const info = listingHistoryInfo(
    { vin: "VIN1" },
    {
      snapshots: [
        { date: "2026-09-19", vins: ["VIN1"] },
        { date: "2026-09-20", vins: ["VIN1"] }
      ],
      vehicles: {
        VIN1: {
          observations: [
            { date: "2026-09-19", price: 50000 },
            { date: "2026-09-20", price: 48000 }
          ]
        }
      }
    }
  );

  assert.equal(info.wasInPrevious, true);
  assert.equal(info.priceDelta, -2000);
});

test("allows new HTTPS dealer domains and labels known marketplaces", () => {
  assert.deepEqual(
    listingDestination("https://newdealer.example/vehicle/123", ["autolist.com"]),
    { type: "dealer", url: "https://newdealer.example/vehicle/123" }
  );
  assert.equal(
    listingDestination("https://www.autolist.com/vehicle/123", ["autolist.com"]).type,
    "marketplace"
  );
  assert.equal(
    listingDestination("https://www.carfax.com/vehicle/VIN", ["autolist.com"]).type,
    "missing"
  );
  assert.equal(
    listingDestination("http://newdealer.example/vehicle/123", ["autolist.com"]).type,
    "missing"
  );
});
