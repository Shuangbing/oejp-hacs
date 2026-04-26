# Octo Energy JP Home Assistant Integration (HACS)

This custom integration pulls delayed half-hour electricity usage from the Octopus Energy Japan GraphQL API and exposes it in Home Assistant.

## Features

- UI config flow (no credentials in YAML)
- Polling-based sync for delayed API data
- Keeps API timestamps (`startAt` / `endAt`) in sensor attributes
- Time handling aligned to `Asia/Tokyo` (JST) for daily totals

## Installation

1. Add this repository to HACS as a custom repository (`Integration` type).
2. Install **Octo Energy JP** from HACS.
3. Restart Home Assistant.
4. Go to `Settings` -> `Devices & Services` -> `Add Integration` -> `Octo Energy JP`.
5. Enter your Octopus Energy JP email/password in the UI.

## Entities

- `sensor.octo_energy_jp_latest_half_hour_usage`
  - Latest half-hour usage in kWh.
  - Attributes include original API timestamps and recent readings.
- `sensor.octo_energy_jp_today_total_usage`
  - Total usage for current JST day.
- `sensor.octo_energy_jp_latest_data_timestamp`
  - Timestamp of latest data point received from API.

## Notes about delayed data

The Octopus API may lag by several hours. This integration intentionally treats API timestamps as source-of-truth and surfaces delay information in entity attributes.
