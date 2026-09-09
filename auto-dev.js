import { renderInventory } from "./lib/inventory-view-v2.js";

const isLocalCacheServer = ["127.0.0.1", "localhost", "[::1]"].includes(location.hostname)
  && location.port === "4174";

if (!isLocalCacheServer) {
  location.replace("./");
} else {
  const [configResponse, inventoryResponse] = await Promise.all([
    fetch("./data/site-config.json", { cache: "no-store" }),
    fetch("./api/auto-dev-inventory", { cache: "no-store" })
  ]);
  if (!configResponse.ok) {
    throw new Error(`Site configuration request failed with HTTP ${configResponse.status}`);
  }
  if (!inventoryResponse.ok) {
    throw new Error(`Inventory request failed with HTTP ${inventoryResponse.status}`);
  }
  renderInventory(await inventoryResponse.json(), await configResponse.json());
}
