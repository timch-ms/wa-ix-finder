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

## Inventory data

Listings and source status are stored in `data/listings.json`. Run `npm run refresh` to check whether configured dealer inventory pages are reachable. The refresh never interprets a blocked request as zero inventory and never deletes existing records.

Dealer websites commonly block automated requests or render inventory through private APIs. Records therefore include a `verifiedAt` date, package evidence, and a direct dealer URL. DAPP is only `true` when the package is explicitly named. Sensatec and leatherette are classified as synthetic, never as genuine leather.

## Publish

Create a GitHub repository, push the `main` branch, and select **GitHub Actions** under **Settings → Pages → Build and deployment**. The included workflow deploys the static site.
