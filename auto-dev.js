import { renderInventory } from "./lib/auto-dev-view.js";

const isLocalCacheServer = ["127.0.0.1", "localhost", "[::1]"].includes(location.hostname)
  && location.port === "4174";

if (!isLocalCacheServer) {
  location.replace("./");
} else {
  const response = await fetch("./api/auto-dev-inventory", { cache: "no-store" });
  if (!response.ok) throw new Error(`Inventory request failed with HTTP ${response.status}`);
  renderInventory(await response.json());
}
