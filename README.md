# WA iX Finder

An ad-free, static inventory view for used BMW iX listings at Washington dealerships. It is intentionally limited to dealership, year, mileage, exterior color, interior material, and confirmed Driving Assistance Professional Package (DAPP) filtering.

**Public site:** https://timch-ms.github.io/wa-ix-finder/

## Run locally

```powershell
npm test
npm run serve
```

For the static site, open `http://127.0.0.1:4173`. The site has no runtime dependencies and can be hosted directly on GitHub Pages.

## Collect from rendered Edge tabs

Dealer sites that reject server requests can be collected locally from their normal rendered pages:

```powershell
.\scripts\start-collector.ps1
```

This starts the local collector and launches Edge with the unpacked extension in `extension/`, using a dedicated browser profile. It covers Washington's BMW dealers plus BMW of Portland and BMW of Tigard. The extension scans inventory cards, opens discovered iX detail pages in inactive tabs, and posts normalized public listing data to `http://127.0.0.1:4173/api/collect`. Collector-owned tabs carry a temporary `waixcollector=1` query marker and close after successful collection; the marker is removed from saved dealer links. Dealer pages opened normally—such as by clicking **Get More Information**—are never closed by the extension. The localhost results tab stays open and polls for updates every five seconds.

The collection server stores browser results in `data/collected.json`. It does not access or export Edge cookies. Only public vehicle fields and dealer URLs are retained.

## Auto.dev comparison site

The separate Auto.dev view uses only the Washington BMW iX records returned by the listings API:

```powershell
.\scripts\start-auto-dev.ps1
```

The launcher securely prompts for the API key when `AUTO_DEV_API_KEY` is not already set, starts the cache server, and opens `http://127.0.0.1:4174/auto-dev.html` in Edge. The key is inherited by the server process but is never written to the repository or cache. Running the launcher again reuses the existing server rather than creating another process.

The server stores a sanitized response in ignored file `data/auto-dev-cache.json`. It requests the first result page to determine the actual page size and total, requests each remaining page once, and records the attempt before making requests. Additional page loads on the same local calendar day use the cache without spending API calls. If the server remains running across midnight, it performs one refresh shortly after midnight. After rotating the key, stop the exact server PID shown by the launcher with `Stop-Process -Id <PID>`, then run the launcher again so future refreshes use the new credential.

The Auto.dev page substitutes filters supported by its data—trim, price, interior color, CPO status, one-owner status, accident history, prior usage, listing recency, photo count, and BMW-dealer-only—for unavailable upholstery-material and DAPP fields. Listings first observed after the initial cache are highlighted as new.

Each card exposes its CARFAX report separately. **Dealer Site** is reserved for confirmed dealer or dealer-group domains; marketplace links are labeled as such, and records with only a CARFAX destination do not show a misleading dealer action.

To replace the public snapshot with the current sanitized cache, run:

```powershell
python .\scripts\export-auto-dev-snapshot.py
```

This writes tracked file `data/inventory.json`. GitHub Pages loads that static file through `site-v3.js` with browser caching disabled; the published browser code contains no provider or localhost API request.

## Automated daily refresh

The `Refresh daily inventory` GitHub Actions workflow runs at 16:30 UTC each day and can also be started manually. Add the API credential as a repository Actions secret named `INVENTORY_API_KEY` under **Settings → Secrets and variables → Actions**. The key is passed only to the refresh process and is never written to the snapshot or Pages artifact.

Before making any request, the workflow commits the Washington calendar date to `data/refresh-state.json`. This durable reservation prevents scheduled retries and manual reruns from spending more calls on the same day. A refresh is capped at ten API calls; if more pages would be required, a request fails, or the result count falls implausibly, the prior public snapshot is retained. A successful run sanitizes and tests `data/inventory.json`, commits it to `main`, and deploys the same explicit Pages allowlist used by the normal deployment workflow.

Vehicle-specific make, model, minimum year, labels, official-dealer matching, and approved listing domains are defined in `data/site-config.json`. That public configuration contains no API credentials or provider endpoint.

Verified discrepancies are stored by VIN in `data/listing-overrides.json`. The local cache server and snapshot exporter apply these corrections after each feed refresh so confirmed dealer status and links are not overwritten by stale source fields.

## Inventory data

Listings and source status are stored in `data/listings.json`. Run `npm run refresh` to check whether configured dealer inventory pages are reachable. The refresh never interprets a blocked request as zero inventory and never deletes existing records.

Dealer websites commonly block automated requests or render inventory through private APIs. Records therefore include a `verifiedAt` date, package evidence, and a direct dealer URL. DAPP is only `true` when the package is explicitly named. Sensatec and leatherette are classified as synthetic, never as genuine leather.

## Publish

Create a GitHub repository, push the `main` branch, and select **GitHub Actions** under **Settings → Pages → Build and deployment**. The included workflow deploys the static site.
