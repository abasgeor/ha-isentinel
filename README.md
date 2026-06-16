# ha-isentinel — iSentinel LP Gas Tanks for Home Assistant

Home Assistant integration for [iSentinel](https://www.isentinel.com.mx) battery
LP-gas **tank level** monitors (the ESP/Sigfox sensors read by the iSentinel app).

Polls the iSentinel cloud (`api.isentinel.mx`) and exposes, per tank:

- **Tank level (%)** — with attributes: capacity, alert threshold, last measurement,
  and last refill (date, amount, to-%).
- **Battery (%)**, **Signal** (diagnostic).
- **Capacity (L)**, **Last refill** (timestamp).
- **Low gas** binary_sensor (on when level ≤ the tank's alert threshold).
- **Low battery** binary_sensor.

Tanks update roughly every 8–15 h (battery deep-sleep), so polling is every 30 min.

## Multi-site
The account sees all your tanks. During setup you **pick which tank(s)** to expose
on each Home Assistant instance — so each property's HA shows only its own tank(s).

## Install (HACS custom repository)
1. HACS → ⋮ → Custom repositories → add `https://github.com/abasgeor/ha-isentinel`
   (category Integration).
2. Install, restart HA.
3. Settings → Devices & Services → Add Integration → iSentinel → sign in → pick tanks.

## Notes
- `cloud_polling`. Credentials live only in your HA config entry.
- Auth: `POST /users/login` → access token; refreshed by re-login on 401.
