# Printing

## Adding a Printer

Trumid uses PaperCut for managed printing. The release station is in every office near the printers.

### macOS
1. Open System Settings → Printers & Scanners → **Add Printer**.
2. Choose `Trumid-Print` from the list.
3. When prompted for credentials, use your Okta username and password.

### Windows
1. Open Settings → Bluetooth & devices → Printers & scanners.
2. Add `\\print.trumid.internal\Trumid-Print`.
3. Authenticate with your Okta credentials.

## Releasing Print Jobs

1. Send the document to `Trumid-Print` from any application.
2. Walk to any printer.
3. Tap your badge on the badge reader, or sign in with your Okta credentials.
4. Select your job and tap **Print**.

Jobs not released within 24 hours are deleted automatically.

## Common Issues

- **"Hold for authentication"** - your saved password is stale. Open Keychain Access (Mac) or Credential Manager (Windows) and remove the saved `Trumid-Print` credential, then print again.
- **Printer is offline** - try the printer next to it; if all printers in the room are offline, file a ticket. IT can usually restart the print queue remotely.
- **Color printing is greyed out** - color printing requires an approval. Ask your manager to file a ticket.
