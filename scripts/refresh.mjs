import { readFile, writeFile } from "node:fs/promises";

const path = new URL("../data/listings.json", import.meta.url);
const inventory = JSON.parse(await readFile(path, "utf8"));

// Refresh source reachability without deleting curated records. Dealer pages frequently
// reject server-side clients, so a failed request is visible rather than treated as empty stock.
for (const source of inventory.sources) {
  try {
    const response = await fetch(source.url, {
      redirect: "follow",
      headers: { "user-agent": "WA-iX-Finder/1.0 (+GitHub Pages inventory index)" },
      signal: AbortSignal.timeout(15000)
    });
    source.status = response.ok ? "available" : "blocked";
    source.note = response.ok
      ? "Inventory page was reachable during the latest automated check."
      : `Automated check returned HTTP ${response.status}; existing records were retained.`;
  } catch (error) {
    source.status = "blocked";
    source.note = `Automated check failed (${error.name}); existing records were retained.`;
  }
}

inventory.updatedAt = new Date().toISOString();
await writeFile(path, `${JSON.stringify(inventory, null, 2)}\n`);
console.log(`Checked ${inventory.sources.length} dealer sources; retained ${inventory.listings.length} listings.`);
