# New Laptop Setup

## First Boot Checklist

1. Power on the laptop and connect to a wired ethernet port if available, otherwise use `Trumid-Guest` for the initial setup.
2. Sign in with the temporary credentials printed on the card included with your laptop.
3. When prompted, change your password immediately - see [Password Reset Instructions](password_reset.md) for requirements.
4. Enroll in Okta Verify on your phone (download from the App Store / Play Store).
5. Run **Self Service** (the orange Trumid icon in your Applications folder or Start menu) and install:
   - Slack
   - Zoom
   - Cisco AnyConnect
   - 1Password
   - Chrome and Firefox

## Software You Need on Day One

| Tool       | Where to install        | Notes                                 |
| ---------- | ----------------------- | ------------------------------------- |
| Slack      | Self Service            | Sign in to `trumid.slack.com`         |
| Zoom       | Self Service            | Sign in via Okta SSO                  |
| AnyConnect | Self Service            | Required for VPN                      |
| 1Password  | Self Service            | Use the invite from your IT welcome email |
| Okta Verify| Phone app store          | Required to access any Trumid system  |

## Hardware Issues

### Laptop won't turn on
- Hold the power button for 10 seconds, then press it once.
- Plug into power for at least 5 minutes and try again.
- If still nothing, open a ticket - this requires hands-on help from IT.

### External monitor not detected
- Try a different cable (HDMI vs USB-C); cables fail more often than ports.
- Sleep / wake the laptop with the monitor plugged in.
- For docking stations, unplug and replug the dock power before the data cable.

### Keyboard or trackpad unresponsive
- Reboot the laptop. This resolves the issue ~80% of the time.
- If it persists, run Apple Diagnostics (hold `D` at boot) on Macs, or `mdsched.exe` on Windows.
