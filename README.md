# Akahu — Home Assistant integration

Custom integration that connects to the [Akahu](https://akahu.nz) Personal API and exposes each linked bank account as a balance sensor.

Accounts are grouped under one "service" device per bank connection, so multiple
accounts at the same bank share a single device under the config entry.

## Configuration

1. Create a personal app in the [Akahu developer portal](https://my.akahu.nz/developers) and copy the **App ID token** and **User access token**.
2. In Home Assistant, go to **Settings → Devices & Services → Add Integration** and search for **Akahu**.
3. Paste the two tokens. The integration fetches your profile to identify the account, then creates a sensor per connected account.

Balances refresh every 10 minutes.

## Installation

### HACS (custom repository)

1. In HACS, open the three-dot menu → **Custom repositories**.
2. Add `https://github.com/jesserockz/home-assistant-akahu` as an **Integration** repository.
3. Install **Akahu**, then restart Home Assistant.

### Manual

Copy `custom_components/akahu/` into your Home Assistant `config/custom_components/` directory and restart Home Assistant.
