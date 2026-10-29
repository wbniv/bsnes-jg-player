# Publish Android APK downloads to Cloudflare R2

**Status:** Proposed. No Android APKs are currently published for public download. The next user-directed web release should build the web app and two Native Android APKs, publish the APKs and download page to a dedicated R2 bucket, and retain exactly the current and previous release.

## Goal

Give people a stable public HTTPS page for downloading the SNES Android app when nearby transfer or the temporary same-Wi-Fi QR transfer is unavailable or unsuccessful. The R2 page must offer the current and previous release, clearly identify the Native library and Native player APKs, and state the version and SHA-256 for each file.

Make the release page discoverable directly from [`https://biohack.net/snes/`](https://biohack.net/snes/): add a clearly labeled Android APK download link and a scannable QR code that opens the stable R2 release page. The page offers both Native APK variants, so the QR encodes the landing-page URL rather than choosing or linking to one versioned APK.

The Android library APKs bundle the ROM catalog, ROM files, and preview art; downloading either library APK also delivers those assets. The standalone player APKs contain only their configured single-ROM app build. The web build remains a web app and is not represented as an APK.

## Current state

- The current Android build can produce four artifacts, but Android WASM is too slow for usable playback and is excluded from public distribution. The public release contains only `bsnes-jg_llvm-65816-torture-test-suite-on-snes-v<version>.apk` (Native library) and `bsnes-jg_mandelbrot-v<version>.apk` (Native player).
- The Native library APK includes the published ROM assets. Its payload and SHA-256 must be recorded per release. The Native player contains only its configured single-ROM build.
- Browser WASM remains a separate web target and is included in the web release; this policy does not remove it.
- `versionName` and `versionCode` are currently fixed in Gradle. The release workflow needs a real versioning policy and must reject duplicate or non-increasing Android `versionCode` values.
- Controlled device builds currently use the local debug signing key. Public releases need a durable, backed-up release key and a single signing path so future updates install over earlier public versions.
- Proposed public R2 host: `https://downloads.biohack.net/bsnes-jg/`. The R2 bucket and custom-domain binding are not provisioned yet; confirm the DNS route and Cloudflare ownership during setup. The public project presence should link from the existing `biohack.net` SNES area and from `https://wald3n.com/open-source`. The `/snes/` page needs both a visible download link and a QR code to the release landing page.

## Release task contract

Add project-scoped secret tasks and an explicit root Task command, **`task web:release`**, for the next user-directed public web release. This command is the single release entry point; a normal local web or Android build must not upload anything to R2. The release task uses Task's interactive `prompt:` confirmation to state that it will publish the current web build and two Native APKs and prune releases older than current/previous.

The release task will:

1. Build the web player and the two Native Android release APKs from the same release version. Do not package Android WASM APKs for public distribution.
2. Require the configured release signing key; fail if any APK is signed by the debug key or has a mismatched package/variant identity.
3. Inspect both APKs, verify the Native library's bundled ROM assets, calculate SHA-256 and file size, and generate release metadata.
4. Upload versioned artifacts to the dedicated R2 bucket and verify every uploaded object's size and hash.
5. Publish the manifest and download page only after the uploaded objects pass verification.
6. Prune every release older than the new current and previous versions. The task reports failure if pruning did not complete; it never treats a partially published release as success.

The exact Taskfile dependencies may call the existing Android container build and the project's web build. Public publication must remain a separate, intentional release operation rather than a side effect of `task build` or `task android-tv:build`.

Follow the existing project secret workflow: `task secrets-pull` renders the gitignored, mode-`0600` local `.env` cache from AWS SSM SecureString parameters, and Task loads that cache with its `dotenv` directive. SSM is the source of truth; `.env` is read-only generated cache. Store the account ID and R2 endpoint alongside the project-specific R2 access key ID and secret key under a project-scoped SSM prefix. The account ID should come from this cache/auth configuration; never ask the user to look it up or type it. If the bucket-scoped key pair is not provisioned, `task secrets-bootstrap` is the one-time path to seed SSM, with key values entered through hidden prompts and never printed. Publication passes the cached values to the R2 client as environment configuration; no credential appears in task arguments or logs.

Add `task web:r2:setup` for the idempotent one-time bucket/domain setup and `task web:release:check` for read-only configuration, manifest, hash, and cache-header inspection. Setup must show the project bucket and intended permissions, then ask before creating/changing resources. `task web:release` has a separate `prompt:` naming the destination and explaining the prune behavior.

```sh
# Run only when explicitly asked for a public web release.
task web:release
```

## Public object layout

Use a dedicated bucket, for example `bsnes-jg-downloads`, with the read-only custom domain `downloads.biohack.net`. Give the publishing task credentials that can write only to this bucket. Serve the small static download page and manifest from the same R2 prefix as the APKs, so the QR, version index, and APK links share one HTTPS origin. On `https://biohack.net/snes/`, add a prominent, clearly named Android APK download link and a QR code that encodes `https://downloads.biohack.net/bsnes-jg/`; keep the human-readable URL beside the QR. The QR must lead to the variant-selection page, where visitors can choose Native library or Native player and review version, size, and SHA-256. Also add a project entry on `wald3n.com/open-source` linking to both the source repository and the download page.

Proposed keys:

```text
bsnes-jg/index.html
bsnes-jg/current.json
bsnes-jg/releases/<version>/release.json
bsnes-jg/releases/<version>/bsnes-jg_llvm-65816-torture-test-suite-on-snes-v<version>.apk
bsnes-jg/releases/<version>/bsnes-jg_mandelbrot-v<version>.apk
```

There are no Android WASM APK keys: those builds are too slow for usable playback and are excluded from distribution. Browser WASM remains the web app on biohack.net; this R2 release prefix contains the download page/manifest and the two Native Android APKs.

`current.json` is the only mutable release pointer. It lists both `current` and `previous`; each release record includes the version name, Android version code, publish timestamp, and each APK's display name, package ID, engine, player/library type, byte size, SHA-256, and versioned URL. The landing page reads this manifest to render the two Native download buttons and QR codes. Follow the established static-site cache split: mutable `index.html` and `current.json` use `Cache-Control: no-store` (or `max-age=0, must-revalidate` where a CDN requires revalidation); versioned APKs and release manifests use `public, max-age=31536000, immutable`.

Use `downloads.biohack.net/bsnes-jg/` as the proposed stable download URL. Verify the Cloudflare R2 custom-domain binding, DNS, and HTTPS certificate before enabling it in the app or treating the how-to link as live.

## Publication sequence and atomicity

Upload APKs under a new version prefix first. The versioned files can be checked before they appear in `current.json`. Download each staged public object back through the public HTTPS route and compare byte count and SHA-256 with the local build. Only after both match, publish the new release record and atomically replace `current.json` with `{current: new, previous: old-current}`. Then delete every release not named by that index.

If upload or verification fails, leave `current.json` unchanged and do not delete the old files. If index publication succeeds but pruning fails, the current and previous links still work; the task must fail with a cleanup-pending status and safely retry pruning on the next invocation. Limit pruning to the dedicated `bsnes-jg/` prefix and the versions absent from the validated current/previous manifest; never run broad sync against another project or bucket.

![Release build, verification, publication, and retention order](assets/r2-apk-release-pipeline.svg)

### Two-version retention

For each successful release, shift the old current to previous and remove the version that falls out of the pair. The release manifest is the source of truth for pruning; it must not infer versions from loose filename sorting.

### Download and QR route

The static R2 page is the public fallback for Android phone/tablet and Chromecast. Direct Android Sharesheet/Quick Share and the temporary local QR route remain the preferred transfer methods. If those routes cannot transfer the APK, the app can show a QR for the public download page; the recipient selects the Native library or Native player APK there. This public route works across different networks and delivers the latest signed release, which may be newer than the sender's currently installed APK.

The in-app public QR and the QR on `biohack.net/snes/` must encode only the stable HTTPS landing-page URL, never an APK filesystem path or the temporary LAN server address. Keep a human-readable URL beside each QR. The SNES page's download link and QR both lead to the same variant-selection page; the web app does not attempt to read an installed Android APK.

![Phone, TV, and browser clients download signed APK artifacts from the public R2 page](assets/r2-apk-download-topology.svg)

## Signing, identity, and ROM payload

- Establish one durable release signing key, owner, backup, and recovery procedure before the first public upload. Do not publish the controlled-build debug-signed APKs.
- Keep package IDs stable within each distributed variant. Increment `versionCode` monotonically and set one release `versionName` across both APKs.
- Preserve the app titles in downloaded filenames: `bsnes-jg_llvm-65816-torture-test-suite-on-snes-v<version>.apk` for the Native library, and `bsnes-jg_mandelbrot-v<version>.apk` for the Native player. Label the variants Native library and Native player on the landing page. Android WASM builds are not public release variants because their playback performance is unusable.
- Before upload, inspect both APKs. Verify that the Native library APK contains the expected catalog, ROM files, and preview cards; record the verified asset counts in `release.json`. Do not claim that the Native player includes the full ROM library.
- Report SHA-256 and byte size beside each download. After downloading, the recipient should be able to compare the advertised hash before installation.
- Android's normal installer remains responsible for the recipient's explicit install approval. The public page transfers a file; it does not install it silently.

## R2 security and operations

- Provision a dedicated R2 bucket and project-owned public custom domain. Keep bucket writes authenticated; allow anonymous reads only for the published page, manifest, and retained release objects.
- Keep the account ID, R2 endpoint, and bucket-scoped key pair in project-scoped SSM SecureString parameters; use the gitignored `.env` only as a generated local cache. Do not put credentials in the repository, task arguments, logs, or generated HTML.
- Match the existing Task conventions: one-time setup has an explicit confirmation before changing credentials or creating a bucket; publication has a `prompt:` naming the destination and explaining current/previous pruning. `task web:release:check` must remain read-only.
- Limit cleanup to `bsnes-jg/releases/` and compare candidate deletions against the two release IDs in `current.json`.
- Log the release version, APK hashes, R2 object keys, publish result, and prune result without logging credentials.
- A rollback changes the release index to point to the already-retained previous release. Do not rebuild or mutate a versioned artifact to roll back.
- Do not accept user-uploaded APKs, ROMs, or arbitrary paths in this public bucket. It is a static release distribution point only.

## Plan of work

1. Confirm `downloads.biohack.net`, choose the dedicated bucket name, and determine infrastructure/config ownership. Pull the account ID from existing SSM/cache configuration rather than asking the user for it.
2. Define and provision the durable release signing key. Keep controlled test signing separate.
3. Replace the fixed Android version fields with one version source and add monotonic version-code validation.
4. Add the two-APK inspection/manifest generation step, including the Native library ROM payload checks and SHA-256.
5. Add project-scoped `task secrets-pull` and `task secrets-bootstrap` wiring for SSM and the local `.env` cache; add `task web:r2:setup` for the project bucket/domain and least-privilege permissions.
6. Implement `task web:release` with staged upload, public HTTPS verification, manifest-last publication, two-version pruning, and retry-safe cleanup.
7. Add the static landing page at `downloads.biohack.net/bsnes-jg/` with two clearly named Native variants, current/previous release labels, SHA-256/size, and QR codes for the page URL.
8. After the public route passes HTTPS checks, set `PUBLIC_ANDROID_DOWNLOAD_URL=https://downloads.biohack.net/bsnes-jg/` in the biohack.net production build environment. This renders the gated download link and build-generated QR on `https://biohack.net/snes/`; invalid URLs fail the site build. Also link from `wald3n.com/open-source` to the source repository and download page. Identify this repository as the emulator/player project, not as the separate packaged-upstream `bsnes-jg` APT package.
9. Add the public-download QR fallback to Android phone/tablet and Chromecast share flows. Use Quick Share for direct phone-to-phone transfer and local QR when both devices share a network; show the public QR when those routes are unavailable or fail. The sender never uploads the APK through this fallback; the recipient downloads the published copy from R2.
10. Update `docs/how-to/share-the-app.md` to the verified URL and capture proof for current/previous release links, both APK files and hashes, Native library ROM payload, biohack.net and wald3n.com links, phone and TV scans, recipient install approval, and successful removal of the older third release.

## Proof checklist

- [ ] `task web:release` builds browser WASM and two Native Android APKs from one release version; Android WASM APKs are excluded from public distribution.
- [ ] The release task refuses debug signing, duplicate/non-increasing version codes, package/variant mismatches, incomplete ROM-library APKs, and hash mismatches.
- [ ] `downloads.biohack.net/bsnes-jg/` serves the landing page and `current.json` over HTTPS; all APK URLs work without credentials.
- [ ] The index shows exactly current and previous versions, with both Native APKs, hashes, and sizes.
- [ ] A new release changes the index only after both APKs have been uploaded and fetched back with matching hashes.
- [ ] After publishing a third version, R2 contains only the current and previous release artifacts under `bsnes-jg/releases/`.
- [ ] Failure before manifest publication leaves existing current/previous downloads intact. Failure during pruning is reported and retryable.
- [ ] `https://biohack.net/snes/` displays a clearly labeled Android APK download link and QR code; both open `https://downloads.biohack.net/bsnes-jg/`, where visitors can choose either Native APK and verify its version, size, and SHA-256.
- [ ] The `/snes/` QR is scannable from a second device, has an adjacent readable URL, and remains usable at desktop and mobile page widths.
- [ ] The `/snes/` APK section remains absent when `PUBLIC_ANDROID_DOWNLOAD_URL` is unset, and the build rejects a configured URL outside the verified HTTPS release page.
- [ ] `wald3n.com/open-source` links to both the project source and the public download page.
- [ ] A phone can scan the public page QR from a different network and download the selected APK.
- [ ] Chromecast offers public QR when local transfer is unavailable or unsuccessful; the QR displays a readable HTTPS URL.
- [ ] Quick Share transfers directly without internet or sender cellular data; if it and local QR are unavailable, the recipient can scan the public QR and download over mobile data without a sender upload.
- [ ] The recipient's Native library APK includes its ROM catalog and files and installs through Android's normal confirmation flow.
- [ ] The bucket, credentials, domain, and pruning scope belong only to this project.

## Open decisions

- Verify the proposed `downloads.biohack.net` R2 custom-domain binding and HTTPS route.
- Choose the R2 bucket name and where its infrastructure is managed.
- Select the release-signing key owner, backup, and local/CI signing workflow.
- Decide whether the public page initially labels the Native library build “Recommended” or presents both Native variants equally.
