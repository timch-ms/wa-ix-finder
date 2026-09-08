import { renderInventory } from "./lib/auto-dev-view.js";

const response = await fetch("./data/auto-dev-listings.json");
if (!response.ok) throw new Error(`Static inventory request failed with HTTP ${response.status}`);
renderInventory(await response.json());
