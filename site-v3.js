import { renderInventory } from "./lib/inventory-view-v2.js";

const [configResponse, inventoryResponse, historyResponse] = await Promise.all([
  fetch("./data/site-config.json", { cache: "no-store" }),
  fetch("./data/inventory.json", { cache: "no-store" }),
  fetch("./data/inventory-history.json", { cache: "no-store" })
]);
if (!configResponse.ok) {
  throw new Error(`Site configuration request failed with HTTP ${configResponse.status}`);
}
if (!inventoryResponse.ok) {
  throw new Error(`Static inventory request failed with HTTP ${inventoryResponse.status}`);
}

const config = await configResponse.json();
const history = historyResponse.ok
  ? await historyResponse.json()
  : { snapshots: [], vehicles: {} };
const vehicleName = config.vehicleName || `${config.make} ${config.model}`;
document.title = config.siteTitle;
document.querySelector("#site-description").content =
  `Used ${vehicleName} listings in Washington from a daily inventory snapshot.`;
document.querySelector("#brand-link").ariaLabel = `${config.siteTitle} home`;
document.querySelector("#brand-mark").textContent = config.brandMark;
document.querySelector("#brand-name").textContent = config.siteTitle.replace(/^WA\s+/, "WA ");
document.querySelector("#hero-title").textContent = `Washington ${vehicleName} listings`;
document.querySelector("#results-eyebrow").textContent =
  `USED ${vehicleName.toUpperCase()} · WASHINGTON`;
document.querySelector("#dealer-only-label").textContent = config.dealerOnlyLabel;
document.querySelector("#dealer-only-description").textContent = config.dealerOnlyDescription;

renderInventory(await inventoryResponse.json(), config, history);
