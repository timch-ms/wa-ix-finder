const DEALERS = {
  "www.bmwseattle.com": ["BMW Seattle", "Seattle"],
  "www.bmwbellevue.com": ["BMW of Bellevue", "Bellevue"],
  "bmwnorthwest.com": ["BMW Northwest", "Fife"],
  "www.bmwlynnwood.com": ["BMW of Lynnwood", "Lynnwood"],
  "www.bmwtricities.com": ["BMW of Tri-Cities", "Richland"],
  "www.bmwofspokane.com": ["BMW of Spokane", "Spokane"],
  "www.bmwofportland.com": ["BMW of Portland", "Portland"],
  "www.bmwportland.com": ["BMW of Portland", "Portland"],
  "www.bmwtigard.com": ["BMW of Tigard", "Tigard"]
};

const [dealer, city] = DEALERS[location.hostname] || [];
const VIN_PATTERN = /\b([A-HJ-NPR-Z0-9]{17})\b/i;
const TITLE_PATTERN = /\b(20(?:2[2-9]|30))\s+BMW\s+iX(?:\s+(xDrive(?:40|45|50|60)|M60|M70))?/i;
const COLLECTOR_PARAMETER = "waixcollector";
let scanCount = 0;

function publicUrl(value) {
  const url = new URL(value);
  url.searchParams.delete(COLLECTOR_PARAMETER);
  if (url.hash === "#wa-ix-collector" || url.hash === "#") url.hash = "";
  return url.toString();
}

function numericValues(text, pattern) {
  return [...text.matchAll(pattern)]
    .map((match) => Number(match[1].replace(/,/g, "")))
    .filter(Number.isFinite);
}

function labeledValue(lines, labels) {
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    for (const label of labels) {
      const inline = line.match(new RegExp(`^${label}\\s*:?\\s*(.+)$`, "i"));
      if (inline?.[1] && !/^(?:color|360°?|ext\.?|int\.?)$/i.test(inline[1].trim())) return inline[1].trim();
      if (new RegExp(`^${label}\\s*:?$`, "i").test(line) && lines[index + 1]
        && !/^(?:color|360°?|ext\.?|int\.?)$/i.test(lines[index + 1])) return lines[index + 1];
    }
  }
  return "Not listed";
}

function bestImage(root) {
  const images = [...root.querySelectorAll("img")];
  const image = images.find((item) =>
    item.naturalWidth >= 400
    && !/logo|icon|pixel|avatar/i.test(`${item.alt} ${item.src}`)
  ) || images.find((item) => /vehicle|inventory|vauto|dealerinspire|dealercdn/i.test(item.currentSrc || item.src));
  return image?.currentSrc || image?.src || "assets/ix-blue.svg";
}

function walk(value, visit) {
  if (!value || typeof value !== "object") return;
  visit(value);
  Object.values(value).forEach((child) => walk(child, visit));
}

function structuredData() {
  const listings = [];
  const detailUrls = new Set();
  for (const script of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      walk(JSON.parse(script.textContent), (item) => {
        const name = String(item.name || "");
        const itemUrl = item.url || item.offers?.url || item.item?.url;
        if (itemUrl && /\bBMW(?:®)?\s+iX\b/i.test(name)) detailUrls.add(itemUrl);
        const type = Array.isArray(item["@type"]) ? item["@type"].join(" ") : String(item["@type"] || "");
        if (!/\b(?:Vehicle|Car|Product)\b/i.test(type) || !/\bBMW(?:®)?\s+iX\b/i.test(`${name} ${item.model || ""}`)) return;
        const title = name.match(TITLE_PATTERN);
        const price = Number(item.offers?.price || item.offers?.lowPrice);
        const mileage = Number(item.mileageFromOdometer?.value ?? item.odometer);
        if (!title || !price || !Number.isFinite(mileage)) return;
        const description = String(item.description || "");
        const dappMatch = description.match(/Driving Assistance (?:Professional|Pro)(?: Package| Pkg)?/i);
        const image = Array.isArray(item.image) ? item.image[0] : item.image;
        listings.push({
          year: Number(title[1]),
          make: "BMW",
          model: "iX",
          trim: item.vehicleConfiguration || title[2] || "Trim not listed",
          price,
          mileage,
          exteriorColor: item.color || "Not listed",
          interiorMaterial: description.match(/\b(?:Full\s+)?(?:Merino|Vernasca|Nappa)\s+Leather\b|\bSensatec\b|\bLeather\b/i)?.[0] || "Not listed",
          dapp: Boolean(dappMatch),
          dappEvidence: dappMatch?.[0] || "Package not confirmed in structured listing",
          url: itemUrl || location.href,
          image: image || "assets/ix-blue.svg",
          vin: item.vehicleIdentificationNumber || item.identifier || null
        });
      });
    } catch {
      // Invalid third-party JSON-LD blocks are ignored.
    }
  }
  return { listings, detailUrls: [...detailUrls] };
}

function parseListing(root, url) {
  const text = root.innerText?.replace(/\u00a0/g, " ") || "";
  const vehicleData = root.matches?.("[data-vehicle-information], [data-vehicle]")
    ? root
    : root.querySelector?.("[data-vehicle-information], [data-vehicle]");
  const dataTitle = vehicleData?.dataset?.name
    || [vehicleData?.dataset?.year, vehicleData?.dataset?.make, vehicleData?.dataset?.model, vehicleData?.dataset?.trim]
      .filter(Boolean).join(" ");
  const title = dataTitle.match(TITLE_PATTERN)
    || text.match(TITLE_PATTERN)
    || decodeURIComponent(url).replace(/[-_/]+/g, " ").match(TITLE_PATTERN);
  if (!title) return null;
  const prices = numericValues(text, /\$\s*([\d,]{4,})/g).filter((value) => value >= 10000 && value <= 200000);
  const mileages = numericValues(text, /\b([\d,]{1,7})\s*(?:mi\.?|miles)\b/gi).filter((value) => value <= 200000);
  const dataPrice = Number(vehicleData?.dataset?.price);
  const mileageElement = root.querySelector?.(".info__item--mileage .info__value, [data-odometer], [data-mileage]");
  const dataMileage = Number(
    vehicleData?.dataset?.odometer
    || mileageElement?.dataset?.odometer
    || mileageElement?.dataset?.mileage
    || mileageElement?.getAttribute("title")?.replace(/,/g, "")
    || mileageElement?.textContent?.replace(/[^\d]/g, "")
  );
  const price = dataPrice >= 10000 ? dataPrice : prices[0];
  const mileage = Number.isFinite(dataMileage) ? dataMileage : mileages[0];
  if (!price || !Number.isFinite(mileage)) return null;
  const lines = text.split(/\n+/).map((line) => line.trim()).filter(Boolean);
  const vin = (text.match(VIN_PATTERN) || decodeURIComponent(url).match(VIN_PATTERN))?.[1]?.toUpperCase() || null;
  const dappMatch = text.match(/Driving Assistance (?:Professional|Pro)(?: Package| Pkg)?/i);
  const interior = labeledValue(lines, ["Interior(?: Color)?", "Upholstery"]);
  const materialMatch = text.match(/\b(?:Full\s+)?(?:Merino|Vernasca|Nappa)\s+Leather\b|\bSensatec\b|\bLeather\b/i);
  return {
    year: Number(title[1]),
    make: "BMW",
    model: "iX",
    trim: title[2] || "Trim not listed",
    price,
    mileage,
    exteriorColor: vehicleData?.dataset?.extcolor || root.dataset?.extcolor || labeledValue(lines, ["Exterior(?: Color)?"]),
    interiorMaterial: materialMatch?.[0] || vehicleData?.dataset?.intcolor || root.dataset?.intcolor || interior,
    dapp: Boolean(dappMatch),
    dappEvidence: dappMatch ? dappMatch[0] : "Package not confirmed on rendered page",
    url,
    image: bestImage(root),
    vin
  };
}

function isDetailPage() {
  return VIN_PATTERN.test(decodeURIComponent(location.href))
    || /\/inventory\/(?:used|certified)-[^/]+\//i.test(location.pathname)
    || /\/(?:certified|used)\/BMW\/20\d{2}-BMW-iX-/i.test(location.pathname)
    || /\/used-[^-]+-20\d{2}-BMW-iX-/i.test(location.pathname);
}

function listingRoots() {
  if (isDetailPage()) return [[document.body, publicUrl(location.href)]];
  const links = [...document.querySelectorAll("a[href]")].filter((link) => {
    let value = link.href.split("?")[0];
    try {
      value = decodeURIComponent(value);
    } catch {
      return false;
    }
    return /\/inventory\/(?:used|certified)-.*bmw-ix/i.test(value)
      || /\/(?:certified|used)\/BMW\/20\d{2}-BMW-iX-/i.test(value)
      || /\/used-[^-]+-20\d{2}-BMW-iX-/i.test(value);
  });
  const unique = new Map();
  for (const link of links) {
    const root = link.closest(
      "article, li, [data-vehicle], [data-vin], [data-vehicle-vin], [class*='vehicle-card'], [class*='vehicleCard'], [class*='inventory-item'], [class*='vehicle-item'], [class*='result-wrap']"
    ) || link.parentElement?.parentElement?.parentElement || link;
    unique.set(link.href.split("?")[0], root);
  }
  return [...unique].map(([url, root]) => [root, url]);
}

function scan(collectionComplete = false) {
  if (scanCount >= 8) return;
  scanCount += 1;
  if (!dealer) return;
  const bodyText = document.body?.innerText || "";
  const blocked = /access denied|verify you are human|request blocked|captcha/i.test(bodyText);
  const structured = structuredData();
  const roots = listingRoots();
  const cardListings = roots.map(([root, url]) => parseListing(root, url)).filter(Boolean);
  const byKey = new Map();
  for (const listing of [...cardListings, ...structured.listings]) {
    const key = listing.vin || listing.url;
    const previous = byKey.get(key) || {};
    const merged = { ...previous, ...listing };
    merged.dapp = Boolean(previous.dapp || listing.dapp);
    if (previous.dapp) merged.dappEvidence = previous.dappEvidence;
    byKey.set(key, merged);
  }
  const listings = [...byKey.values()];
  const detailUrls = new Set(structured.detailUrls);
  for (const [, url] of roots) detailUrls.add(url);
  for (const listing of listings) {
    if (listing.url !== location.href) detailUrls.add(listing.url);
  }
  const emptyConfirmed = /(?:no|0)\s+(?:matching\s+)?vehicles|no results|did not match/i.test(bodyText);
  chrome.runtime.sendMessage({
    type: "inventory",
    payload: {
      dealer,
      city,
      pageUrl: location.href,
      isDetail: isDetailPage(),
      collectorManaged: new URL(location.href).searchParams.get(COLLECTOR_PARAMETER) === "1",
      collectionComplete,
      blocked,
      emptyConfirmed,
      listings,
      detailUrls: [...detailUrls]
    }
  });
}

setTimeout(scan, 4000);
setTimeout(scan, 10000);
setTimeout(scan, 20000);
setTimeout(() => scan(true), 30000);

setTimeout(() => {
  if (isDetailPage()) return;
  const next = [...document.querySelectorAll(".pagination__link, a, button")].find((element) =>
    /^\s*Next\s*$/i.test(element.innerText || "")
    && !element.matches("[disabled], .disabled, [aria-disabled='true']")
  );
  if (next && /vehicles? found/i.test(document.body?.innerText || "")) {
    next.click();
    setTimeout(scan, 6000);
  }
}, 14000);

let mutationTimer;
new MutationObserver(() => {
  clearTimeout(mutationTimer);
  mutationTimer = setTimeout(scan, 2500);
}).observe(document.documentElement, { childList: true, subtree: true });
