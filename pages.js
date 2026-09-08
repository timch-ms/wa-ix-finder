import { renderInventory } from "./lib/inventory-view.js";

const response = await fetch("./data/inventory.json");
if (!response.ok) throw new Error(`Static inventory request failed with HTTP ${response.status}`);
renderInventory(await response.json());
