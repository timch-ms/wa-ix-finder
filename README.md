# WA Vehicle Finder

One ad-free GitHub Pages site for used vehicle inventory at Washington dealerships.

**Public site:** https://timch-ms.github.io/wa-vehicle-finder/

The vehicle selector currently includes BMW iX, Volvo EX90, Volkswagen ID. Buzz, Tesla Model X and Model Y, Toyota Sienna, Mercedes-Benz EQE SUV and EQS SUV, Porsche Macan Electric and Cayenne, and Maserati Grecale.

## Configuration

`data/vehicles.json` is the single source of configuration for every vehicle. Each entry contains its query, labels, approved dealer domains, and refresh policy:

```json
"refresh": {
  "enabled": true,
  "intervalDays": 2,
  "maxApiCalls": 4
}
```

- Set `enabled` to control automatic updates.
- Set `intervalDays` to change update frequency.
- Set `maxApiCalls` to enforce that vehicle's per-refresh query ceiling.

The workflow checks once each day at `09:17 UTC`. A vehicle is queried only when enabled and its configured number of Washington calendar days has elapsed. The three one-shot Macan Electric, Cayenne, and Grecale snapshots are disabled by default.

## Data and history

Each vehicle has an isolated directory under `vehicles/<slug>/` containing:

- `inventory.json` — sanitized current listings.
- `inventory-history.json` — rolling seven-day availability, mileage, and price observations.
- `refresh-state.json` — durable attempt state and known VINs.
- `listing-overrides.json` — verified corrections that survive refreshes.

The public browser reads only the global configuration, current snapshots, and histories. It never calls the inventory provider and receives no credential or refresh state.

## Automated refresh

Add the inventory credential as the repository Actions secret `INVENTORY_API_KEY`. Before any provider call, `.github/workflows/refresh-inventory.yml` commits reservations for all eligible vehicles. Each vehicle retains its prior public snapshot if its refresh fails, exceeds its query cap, or returns an implausibly small result.

Successful refreshes update only that vehicle's snapshot and seven-day history. Failed and skipped refreshes never imply that listings disappeared.

## Local development

```powershell
python -m unittest discover -s test -p "test_*.py"
npm test
npm run serve
```

Open `http://127.0.0.1:4173`. The static site has no runtime dependencies and deploys through `.github/workflows/pages.yml`.
