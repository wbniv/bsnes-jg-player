# Share the SNES app across phone, tablet, Chromecast, and web

**Status:** In progress. All Android player and library pause menus expose Share. Android supports the Android share target, a temporary LAN QR transfer, and an optional public-download QR that is hidden unless a verified release URL is configured at build time. Phones/tablets can choose the share target or LAN QR; Chromecast uses QR directly. The web page has a Web Share/copy-link action. Build, device validation, web QR display, and cross-form-factor proof remain open.

## Goal

Let a user share this app and its bundled ROM library with another Android user from inside the app. A recipient should be able to receive the correct Android APK (including that build's bundled catalog and ROM assets), verify what they received, and install it through Android's normal user-approved installer. Browser users should be able to share the hosted web app and its published ROM library, and reach the Android APK distribution link where appropriate.

For Android, the APK is the transfer unit: ROM-library builds package the catalog, ROM files, and card images inside the APK, so those assets travel with the app. Single-ROM player builds carry only their configured ROM. Device-local preferences (such as favorites) and any future save data are not part of the APK share. On web, sharing the HTTPS link grants access to the site's published app and ROM assets; it does not create an offline download bundle.

## History and current behavior

1. **Original Android implementation:** `Share app APK` was added to the pause menu. Android sent the installed base APK through `ACTION_SEND` with MIME type `application/vnd.android.package-archive`, a read-only content URI, and a temporary read grant. The URI is served by `ApkShareProvider`; it does not expose a filesystem path.
2. **Observed Pixel result:** Android Sharesheet provides nearby file sharing such as Quick Share, so the user can select a recipient and transfer the APK.
3. **Observed Chromecast failure:** Cast1 reports “You don't have an app that can do that.” The Chromecast has no suitable Sharesheet target, so a standard Android share intent cannot be the only TV transfer path.
4. **Expansion in progress:** Android TV now has a proposed user-initiated LAN transfer: show a QR code for a short-lived, token-protected URL that serves only the installed APK. The ROM catalog and ROM assets bundled inside that APK travel with it. Phone and tablet retain Android Sharesheet as the primary action and can use the same QR transfer when no target is available. The Android build container is intentionally offline, so QR generation uses a vendored, licensed dependency.
5. **Public-download fallback:** The Android share menu can offer a QR for the public release page, and a failed local transfer opens that QR automatically when configured. The URL is supplied as the non-secret Gradle property `publicDownloadUrl` (forwarded to the offline container as `ORG_GRADLE_PROJECT_publicDownloadUrl`) and is restricted to the project release host. It defaults to blank, so no dead/unpublished link appears in shipped builds.
6. **Web platform:** A browser cannot read the installed Android APK. Web sharing must share the web app URL, and any APK download/share must use an explicit HTTPS-hosted release artifact rather than pretending the browser can export an installed package.

## User flows by platform

| Platform | Primary share action | Fallback | Recipient result |
|---|---|---|---|
| Android phone | Choose Quick Share for direct device-to-device transfer or show the local QR | If direct transfer is unavailable or fails, show the public download QR | Receive one `.apk` with its bundled ROM library, review it, and approve installation |
| Android tablet | Same as phone; layout adapts to portrait and landscape | If direct transfer is unavailable or fails, show the public download QR with a large scan target and readable URL | Receive one `.apk` with its bundled ROM library, review it, and approve installation |
| Chromecast / Google TV | In-app local QR screen; do not launch an APK Sharesheet with no receiver | If local transfer cannot connect, show the public download QR | Scan the local QR on the same network or the public QR over internet/mobile data, then download the APK and bundled ROM assets |
| Web browser | Use Web Share API to share the HTTPS web app URL when available; otherwise copy/show the URL | Show a QR code for the web app URL. Offer an APK download/share link only when a release APK URL is configured | Open the hosted web app and its published ROM library, or download an explicitly published APK artifact |

On phone and tablet, keep Quick Share and local QR discoverable. Quick Share is direct device-to-device transfer and does not upload the APK or use cellular data. If direct transfer is unavailable or fails, the public release-page QR lets the recipient download the already-published APK; only the recipient needs internet/mobile data. On Chromecast, local QR is primary when both devices share a network, and public QR is the fallback when the local route cannot connect.

## Transfer architecture

### Android phone, tablet, and Chromecast

- Use the existing provider and `ACTION_SEND` flow for the native Sharesheet route. Grant read access only to the specific APK content URI using `FLAG_GRANT_READ_URI_PERMISSION` and `ClipData`.
- Share the installed APK as-is. For the ROM-library variants it contains `roms/library.json`, the bundled `.sfc` files, and preview cards; do not omit or separately re-fetch these when sharing the app. A single-ROM player flavor has its own smaller asset set.
- Use a local transfer server for QR fallback. Start it only after the user selects Share by QR; bind it to the selected private LAN IPv4 address, not every interface.
- The QR payload contains an ephemeral URL such as `http://<private-ip>:<port>/<random-token>/app.apk`. The server returns only the installed app's APK, with APK MIME type, download filename, and content length.
- Use a cryptographically random token. Expire the server after ten minutes, stop it when the user dismisses the transfer screen or the activity exits, and cap successful downloads. Reject all other paths and methods.
- Quick Share is direct device-to-device transfer: Bluetooth discovers nearby devices and local Wi-Fi carries the file. Both radios must be on, but internet and a shared Wi-Fi network are not required. The built-in QR uses a temporary LAN URL and requires the same local network. The public R2 QR opens the stable HTTPS download page and requires internet/mobile data on the recipient.
- Quick Share requires Wi-Fi and Bluetooth radios enabled, but not internet or the same Wi-Fi network. If either radio is off, tell the sender Quick Share needs both; offer the public QR as a download fallback rather than implying the sender must upload the APK.
- Keep WebView remote loads blocked and `usesCleartextTraffic=false`; the HTTP endpoint is an inbound, user-initiated local file transfer, not WebView access to the network.

### Web browser

- Share the public HTTPS application URL through `navigator.share()` when supported; otherwise expose a copyable URL and an app-link QR code.
- Browsers cannot export `ApplicationInfo.sourceDir` or an installed package. If web users must share the Android APK, provide a separate HTTPS release-artifact URL generated by the build/release process. Show its version and SHA-256 next to the download action.
- A web APK link must identify one exact, signed artifact. Do not assemble or mutate APK files in the browser.

## Signing and install behavior

- The package ID and signing certificate must remain stable so a recipient can install future updates without uninstalling and losing app data.
- Current release builds use this machine's local debug signing key for controlled device testing. Before broad sharing, replace that with a durable, backed-up release key and ensure CI/release artifacts use it consistently.
- Android requires the recipient to approve installs from the receiving source (for example, Quick Share, Files, or the browser). The Share button transfers a file; it must not silently install on the recipient's device.
- Provide the APK variant identity in the filename (engine and player/library variant), plus version and SHA-256 in the web download flow. Avoid presenting a WASM package as Native or vice versa.

## Implementation sequence

1. **Record the original flow and failure.** Keep the Sharesheet path for devices with usable targets; note the Chromecast empty-target behavior and preserve the read-only provider boundary.
2. **Build and validate Android LAN/QR transfer.** The offline-compatible QR encoder, short-lived tokenized local server, transfer screen, Chromecast route, and phone/tablet choice between QR and Android Sharesheet are implemented in source. Build the APKs and validate transfer, hash, bundled ROM assets, and recipient installation.
3. **Complete browser sharing.** The web URL now shares with Web Share API/copy-prompt fallback. Add a locally generated QR for that URL. Once the release page is live, configure the biohack.net production build with `PUBLIC_ANDROID_DOWNLOAD_URL=https://downloads.biohack.net/bsnes-jg/`; this reveals the `/snes/` APK link and generated QR. Both target the stable R2 variant-selection page, not a version-specific APK. Keep the APK link hidden until release URL verification passes.
4. **Harden package release metadata.** Establish stable signing, version labels, APK filename, and SHA-256 reporting for shared APKs.
5. **Validate recipient installation.** Transfer the exact file to a second Android device, check its SHA-256, install it through the normal installer, and verify launch. Repeat update-in-place with the next APK signed by the same key.

## Proof and validation

Record evidence in this plan as work completes:

- [ ] Pixel phone, portrait: “Share with another app” opens the Android share sheet; Quick Share transfers directly with Bluetooth and Wi-Fi enabled.
- [ ] Quick Share proof confirms the APK transfers directly without internet or sender cellular data.
- [ ] If Quick Share/local transfer cannot be used, the public HTTPS QR opens the release page; recipient downloads over mobile data without a shared network or sender upload.
- [ ] Pixel phone, landscape: share controls and QR screen remain usable.
- [ ] Android tablet, portrait and landscape: Sharesheet, QR screen, focus/touch targets, and long download URL remain usable.
- [ ] Cast1: `Share app APK` opens a scannable QR screen instead of an empty Sharesheet; a phone on the same Wi-Fi downloads the APK successfully.
- [ ] Web browser: HTTPS app URL shares through Web Share API where supported and through copy/QR fallback elsewhere.
- [ ] `https://biohack.net/snes/` shows the Android APK download link and a scannable QR to the verified R2 variant-selection page; the QR works from a second device at desktop and mobile widths.
- [ ] Web APK action, if enabled: downloaded file hash matches the release manifest and the recipient can install it.
- [ ] Payload: the received library APK has the same hash as the sender's APK and contains the bundled ROM catalog/assets expected for that build.
- [ ] Security: requests without the random token, for a different path, after expiry, or after dismissal are rejected; the server serves only the APK endpoint (which itself contains that build's bundled ROMs), not raw filesystem paths or unrelated app files.
- [ ] Build: all Android variants build in the network-isolated container with pinned local dependencies.

For each device capture, include platform, form factor, orientation, APK variant/hash, transfer route, result, and artifact path. Do not use ROM contents as the proof image; validate the game shell and share UI only.

## Open decisions

- Choose and document the durable release-signing-key owner and backup procedure.
- Decide where signed Android APK release artifacts and their version/hash manifest will live for web users.
- Public download QR is the fallback when direct/local transfer is unavailable or fails; verify the release page is live before exposing that action.
