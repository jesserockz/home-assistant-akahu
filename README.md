# Akahu — Home Assistant integration

Custom integration that connects to the [Akahu](https://akahu.nz) Personal API and exposes each linked bank account as a balance sensor in Home Assistant.

Accounts are grouped under one "service" device per bank connection, so multiple accounts at the same bank share a single device under the config entry.

## Supported devices

Akahu is a New Zealand open-banking aggregator, so the integration does not talk to physical hardware. Instead, it surfaces whichever bank accounts you have connected through your Akahu personal app, including (but not limited to):

- ANZ
- ASB
- BNZ
- Kiwibank
- Westpac
- The Co-operative Bank
- TSB
- Heartland
- Rabobank
- Sharesies, Hatch, and other investment providers exposed via Akahu

Any account that appears in the [Akahu My Connections page](https://my.akahu.nz/connections) and reports a balance is surfaced as a sensor. Account types Akahu does not currently expose a balance for (for example, some credit-card facilities during onboarding) will be skipped until Akahu publishes a balance.

## Supported functions

For each connected account the integration creates:

| Entity | Platform | Description |
| ------ | -------- | ----------- |
| Balance | `sensor` | Current cleared balance of the account, in the account's native currency (typically `NZD`). Uses the `monetary` device class and the `total` state class so it works with Energy/Statistics dashboards and the recorder long-term statistics. |

Each account becomes one sensor under a device named after its bank connection.

## Use cases

- **Cash-flow dashboard** — combine balance sensors with a template sensor that sums everyday accounts to track on-hand cash across every bank in one card.
- **Spending alerts** — trigger a notification when a savings account drops below a threshold, or when the balance changes by more than a configured amount between updates.
- **Net-worth tracking** — feed the long-term statistics into the Statistics graph card to chart balance over weeks/months without writing any history yourself.
- **Budget reconciliation** — pair with a template sensor that subtracts a planned monthly budget from the live balance to see remaining headroom.

## Installation

### HACS (custom repository)

1. In HACS, open the three-dot menu → **Custom repositories**.
2. Add `https://github.com/jesserockz/home-assistant-akahu` as an **Integration** repository.
3. Install **Akahu**, then restart Home Assistant.

### Manual

Copy `custom_components/akahu/` into your Home Assistant `config/custom_components/` directory and restart Home Assistant.

## Configuration

1. Create a personal app in the [Akahu developer portal](https://my.akahu.nz/developers) and copy the **App ID token** and **User access token**.
2. In Home Assistant, go to **Settings → Devices & Services → Add Integration** and search for **Akahu**.
3. Paste the two tokens. The integration fetches your profile to identify the account, then creates a sensor per connected account.

### Installation parameters

| Parameter            | Description                                                                                                                                                          |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **App ID token**     | Identifier of the personal app you create in the [Akahu developer portal](https://my.akahu.nz/developers). Starts with `app_token_`. Used in the `X-Akahu-Id` header. |
| **User access token**| Personal access token issued for your own Akahu user, scoped to the personal app above. Starts with `user_token_`. Sent as a bearer token.                           |

Both tokens are stored in the config entry. If either is rotated in the Akahu portal, Home Assistant will surface a re-authentication notice; you can also update them at any time via **Configure** on the integration tile (see [Reconfiguration](#reconfiguration) below).

### Reconfiguration

Open the integration in **Settings → Devices & Services**, choose **Configure**, and re-enter the two tokens. The unique ID of the entry must match the user the new tokens belong to — pointing the entry at a different Akahu user is rejected.

## Data updates

The integration **polls** the Akahu Personal API every **10 minutes** and uses a single coordinated request per refresh, regardless of how many accounts you have connected.

- Akahu does not push balance updates, so polling is the only available transport.
- 10 minutes is well inside Akahu's published rate limits for personal apps and matches how often most banks themselves refresh balances through Akahu — polling faster would not reveal newer numbers.
- If the API is unreachable, entities are marked unavailable until the next successful poll; balances are *not* extrapolated.
- You can change the polling interval per-entry via **Settings → Devices & Services → Akahu → ⋮ → System options → Update interval**.

When new accounts are connected on the Akahu side they appear automatically on the next refresh — there's no need to reload the integration.

## Examples

Trigger a notification when your everyday account drops below a threshold:

```yaml
automation:
  - alias: "Low balance warning"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.everyday_balance
        below: 250
    actions:
      - action: notify.mobile_app_phone
        data:
          title: "Everyday account is low"
          message: "Balance is {{ states('sensor.everyday_balance') }} NZD"
```

Sum every connected balance into a single net-worth sensor:

```yaml
template:
  - sensor:
      - name: "Net worth"
        unit_of_measurement: "NZD"
        device_class: monetary
        state_class: total
        state: >-
          {{ states.sensor
             | selectattr('attributes.device_class', 'eq', 'monetary')
             | map(attribute='state')
             | map('float', 0)
             | sum | round(2) }}
```

## Known limitations

- **Read-only.** The integration only reads balances. It does not initiate payments, fetch transaction history, or categorise spending — Akahu's write APIs are not exposed.
- **Balance only.** Only a single "current balance" sensor is created per account. Available balance, credit limit, and overdraft state are present in the API but are not surfaced as separate entities.
- **No historical backfill.** Long-term statistics start accumulating from the moment the integration is installed; Akahu's historical balance endpoints are not queried.
- **Currency follows the account.** Multi-currency users will see each account in its native currency; cross-currency totals require a template sensor with your own FX rate.
- **NZ banks only.** Akahu is a New Zealand service. Banks outside NZ are not supported.

## Troubleshooting

### Setup fails with "Invalid authentication"

**Symptom:** The config flow shows *Invalid authentication* when you submit the two tokens.

**Description:** One or both tokens are wrong, swapped, or have been revoked in the Akahu developer portal.

**Resolution:**

1. Open the [Akahu developer portal](https://my.akahu.nz/developers) and select your personal app.
2. Confirm the **App ID token** starts with `app_token_` and the **User access token** starts with `user_token_` — it's easy to paste them into the wrong field.
3. If the user token was revoked, generate a new one in **My Akahu → Connected apps**.
4. Re-enter both values in the Home Assistant config flow.

### Setup fails with "Failed to connect"

**Symptom:** The config flow shows *Failed to connect* even though the tokens look correct.

**Description:** Home Assistant could not reach `https://api.akahu.io`. This is normally a transient DNS or network issue.

**Resolution:**

1. From the Home Assistant host, confirm outbound HTTPS to `api.akahu.io` is reachable (for example via the *SSH & Web Terminal* add-on: `curl -I https://api.akahu.io/v1/me`).
2. If you run a restrictive firewall, allow `api.akahu.io` on port 443.
3. Retry the config flow.

### Re-authentication prompt: "wrong account"

**Symptom:** Re-auth or reconfigure aborts with *The tokens belong to a different Akahu account*.

**Description:** The new tokens belong to a different Akahu user than the one the existing entry was created for. The integration refuses to silently swap users because doing so would break existing automations referencing the original entity IDs.

**Resolution:**

1. Confirm whose Akahu user the new tokens were issued for.
2. If you intended to add a second user, leave the existing entry alone and run **Add integration** again to add a brand-new entry.
3. If you intended to replace the original user, delete the old entry first, then add the new tokens via **Add integration**.

### An account disappeared

**Symptom:** A sensor that previously worked is now marked *unavailable* or has been removed entirely.

**Description:** The account was disconnected on the Akahu side (the bank connection expired, was removed from My Akahu, or Akahu lost access).

**Resolution:**

1. Open the [Akahu My Connections page](https://my.akahu.nz/connections) and reconnect the affected bank if needed.
2. The integration removes devices for accounts that are no longer returned by Akahu; reconnecting will recreate the device and sensor on the next poll.
