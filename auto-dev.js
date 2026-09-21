import { renderInventory } from "./lib/inventory-view-v2.js";

const isLocalCacheServer = ["127.0.0.1", "localhost", "[::1]"].includes(location.hostname)
  && location.port === "4174";

if (!isLocalCacheServer) {
  location.replace("./");
} else {
  const [configResponse, inventoryResponse] = await Promise.all([
    fetch("./data/vehicles.json", { cache: "no-store" }),
    fetch("./api/auto-dev-inventory", { cache: "no-store" })
  ]);
  if (!configResponse.ok) {
    throw new Error(`Site configuration request failed with HTTP ${configResponse.status}`);
  }
  if (!inventoryResponse.ok) {
    throw new Error(`Inventory request failed with HTTP ${inventoryResponse.status}`);
  }
  const siteConfig = await configResponse.json();
  const vehicleConfig = siteConfig.vehicles.find(
    (vehicle) => vehicle.slug === siteConfig.defaultVehicle
  );
  renderInventory(await inventoryResponse.json(), vehicleConfig);
}
