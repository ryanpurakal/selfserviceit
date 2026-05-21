# Office WiFi & Network

## Connecting to Trumid WiFi

There are three SSIDs in every office:

- `Trumid-Corp` - employee laptops and phones (uses Okta SSO)
- `Trumid-Guest` - visitors only, captive portal with daily code from reception
- `Trumid-IoT` - printers, conference room hardware (do not use)

To connect on a corporate laptop:

1. Choose `Trumid-Corp` from the WiFi menu.
2. When prompted, sign in with your Okta credentials.
3. Approve the Okta Verify push.
4. Accept the certificate the first time you connect.

## Common WiFi Problems

### "Authentication failed" on Trumid-Corp
- Make sure you finished password rotation if you got an Okta reminder this week.
- Forget the network and reconnect.
- If you joined Trumid in the last 24 hours, your account may not have synced to the WiFi RADIUS service yet - try again in an hour or open a ticket.

### Slow speeds in conference rooms
- Conference rooms have dedicated APs - move closer to the wall-mounted AP.
- The 5 GHz band is faster but shorter range; sit within ~20 feet of the AP.

### Can't reach internal sites (`*.trumid.internal`)
- You must be on `Trumid-Corp` or connected to the VPN. Guest WiFi cannot reach internal services by design.
