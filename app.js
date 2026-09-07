import { normalizeMaterial, sortListings, uniqueValues } from "./lib/inventory.js";

async function loadInventory() {
  for (const url of ["./api/inventory", "./data/listings.json"]) {
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (response.ok) return response.json();
    } catch {
      // GitHub Pages has no collection API, so the static JSON is the expected fallback.
    }
  }
  throw new Error("Could not load inventory");
}

let data = await loadInventory();

const controls = {
  year: document.querySelector("#year"),
  dealership: document.querySelector("#dealership"),
  mileage: document.querySelector("#mileage"),
  color: document.querySelector("#color"),
  material: document.querySelector("#material"),
  dapp: document.querySelector("#dapp"),
  sort: document.querySelector("#sort")
};
const grid = document.querySelector("#vehicle-grid");
const template = document.querySelector("#vehicle-card-template");

function addOptions(select, values) {
  values.forEach((value) => select.add(new Option(value, value)));
}

function replaceOptions(select, values, defaultLabel) {
  const current = select.value;
  select.replaceChildren(new Option(defaultLabel, ""));
  addOptions(select, values);
  if ([...select.options].some((option) => option.value === current)) select.value = current;
}

function updateOptions() {
  replaceOptions(controls.year, uniqueValues(data.listings, (item) => item.year), "All years");
  replaceOptions(controls.dealership, uniqueValues(data.listings, (item) => item.dealer), "All dealerships");
  replaceOptions(controls.color, uniqueValues(data.listings, (item) => item.exteriorColor), "All colors");
  replaceOptions(
    controls.material,
    uniqueValues(data.listings, (item) => normalizeMaterial(item.interiorMaterial)),
    "All materials"
  );
}

updateOptions();

function matches(listing) {
  return (!controls.year.value || listing.year === Number(controls.year.value))
    && (!controls.dealership.value || listing.dealer === controls.dealership.value)
    && (!controls.mileage.value || listing.mileage <= Number(controls.mileage.value))
    && (!controls.color.value || listing.exteriorColor === controls.color.value)
    && (!controls.material.value || normalizeMaterial(listing.interiorMaterial) === controls.material.value)
    && (!controls.dapp.checked || listing.dapp === true);
}

function fact(label, value) {
  const node = document.createElement("span");
  node.className = "fact";
  node.innerHTML = `<small>${label}</small><span>${value}</span>`;
  return node;
}

function renderCard(listing) {
  const card = template.content.cloneNode(true);
  const image = card.querySelector(".vehicle-image");
  image.src = listing.image;
  image.alt = `${listing.year} BMW iX ${listing.trim} at ${listing.dealer}`;
  card.querySelector(".dealer-name").textContent = `${listing.dealer} · ${listing.city}, WA`;
  card.querySelector(".vehicle-title").textContent = `${listing.year} BMW iX`;
  card.querySelector(".vehicle-subtitle").textContent = listing.trim;
  const facts = card.querySelector(".vehicle-facts");
  facts.append(
    fact("Mileage", `${listing.mileage.toLocaleString()} mi`),
    fact("Exterior", listing.exteriorColor),
    fact("Interior", normalizeMaterial(listing.interiorMaterial)),
    fact("VIN", listing.vin ? `…${listing.vin.slice(-6)}` : "Not listed")
  );
  const packageRow = card.querySelector(".package-row");
  packageRow.className = `package-row ${listing.dapp ? "dapp-yes" : "dapp-unknown"}`;
  packageRow.textContent = listing.dapp
    ? "✓ Driving Assistance Professional Package listed"
    : "Driving Assistance Professional Package not confirmed";
  packageRow.title = listing.dappEvidence;
  card.querySelector(".vehicle-price").textContent = `$${listing.price.toLocaleString()}`;
  const link = card.querySelector(".info-link");
  link.href = listing.url;
  link.setAttribute("aria-label", `Get more information about the ${listing.year} BMW iX at ${listing.dealer}`);
  return card;
}

function activeFilterEntries() {
  return [
    ["year", controls.year.value && `Year: ${controls.year.value}`],
    ["dealership", controls.dealership.value],
    ["mileage", controls.mileage.value && `Up to ${Number(controls.mileage.value).toLocaleString()} mi`],
    ["color", controls.color.value],
    ["material", controls.material.value],
    ["dapp", controls.dapp.checked && "DAPP listed"]
  ].filter(([, label]) => label);
}

function render() {
  const listings = sortListings(data.listings.filter(matches), controls.sort.value);
  grid.replaceChildren(...listings.map(renderCard));
  document.querySelector("#result-count").textContent = listings.length;
  document.querySelector("#empty-state").hidden = listings.length !== 0;

  const chips = activeFilterEntries().map(([key, label]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "filter-chip";
    button.textContent = `${label} ×`;
    button.addEventListener("click", () => {
      controls[key].type === "checkbox" ? controls[key].checked = false : controls[key].value = "";
      render();
    });
    return button;
  });
  document.querySelector("#active-filters").replaceChildren(...chips);
}

Object.values(controls).forEach((control) => control.addEventListener("change", render));
document.querySelector("#clear-filters").addEventListener("click", () => {
  Object.values(controls).forEach((control) => {
    if (control === controls.sort) return;
    control.type === "checkbox" ? control.checked = false : control.value = "";
  });
  render();
});

const sourceList = document.querySelector("#source-list");
function renderSources() {
  const items = data.sources.map((source) => {
    const item = document.createElement("div");
    item.className = `source-item ${source.status}`;
    const link = document.createElement("a");
    link.href = source.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = source.name;
    const status = document.createElement("span");
    status.textContent = source.status === "available" ? "Browser scanned" : source.status === "blocked" ? "Refresh blocked" : "Not scanned";
    const note = document.createElement("small");
    note.textContent = source.note;
    item.append(link, status, note);
    return item;
  });
  sourceList.replaceChildren(...items);
  document.querySelector("#updated-at").textContent =
    `Listing data checked ${new Intl.DateTimeFormat("en-US", { dateStyle: "long" }).format(new Date(data.updatedAt))}.`;
}

renderSources();
render();

setInterval(async () => {
  const refreshed = await loadInventory();
  if (refreshed.updatedAt === data.updatedAt) return;
  data = refreshed;
  updateOptions();
  renderSources();
  render();
}, 5000);
