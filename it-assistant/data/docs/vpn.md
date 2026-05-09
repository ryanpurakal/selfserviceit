# VPN Access Guide

## Connecting to the VPN

1. Open the Cisco AnyConnect client.
2. Enter the VPN address: `vpn.trumid.com`.
3. Authenticate with your Okta credentials and approve the Okta Verify push.
4. Click **Connect**.

You're connected when the AnyConnect tray icon shows a small lock icon.

## Troubleshooting VPN Issues

### Can't connect
- Ensure you're running the latest version of Cisco AnyConnect (4.10 or newer).
- Check your internet connection by loading any non-Trumid site.
- Quit AnyConnect from the system tray, relaunch, and try again.
- If you recently changed your password, sign out of Okta and back in once before retrying.

### Slow VPN speeds
- Connect to a different VPN server from the AnyConnect dropdown (`vpn-us-east`, `vpn-us-west`, `vpn-eu`).
- Close bandwidth-heavy apps (Zoom, Slack huddles, large downloads).
- Test with and without WiFi - a wired connection often resolves throughput issues.
- If speeds remain below 10 Mbps for more than 15 minutes, contact IT.

### "Login failed" errors
- Confirm you can sign in to `okta.trumid.com` from a browser first.
- If Okta works but AnyConnect doesn't, your Okta Verify push may be timing out - approve it within 30 seconds.

## VPN Best Practices

- Always disconnect when not actively working.
- Never share VPN credentials, even with teammates.
- Report any unexpected VPN sessions or password prompts to security@trumid.com immediately.
