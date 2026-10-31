# Prepare and publish a player release

The publisher builds a local candidate, verifies both Native APKs, and publishes only after an explicit destination/prune confirmation. Ordinary build tasks never publish. Android WASM comparison APKs are excluded. Browser npm publication and consumer-site deployment remain separate operations.

## Credentials and signing

`task android:release-secrets-pull` restores the existing durable Android key from SSM. Do not bootstrap another signing identity. `task web:release:signing-recovery` verifies a temporary recovery against the retained signing certificate and removes the temporary key afterward.

R2 publication uses `/indri-studio/bsnes-jg/release/r2` in SSM. `task secrets-pull` creates the ignored mode-0600 `.private/release/r2.json` cache. The publisher reads JSON directly rather than sourcing shell dotenv content. It never passes secrets in command arguments. Provision an **Object Read & Write** R2 key restricted to **bsnes-jg-downloads**, then run `task secrets-bootstrap` in a terminal to enter its key ID/secret through hidden prompts. The account ID is loaded from the existing `/indri-studio/cloudflare/account_id` parameter. Bootstrap refuses to overwrite an existing parameter; rotation requires a separately reviewed replacement.

`task web:r2:setup` checks access to the existing bucket; it does not create domains or grant broader permissions. `task web:r2:probe` writes, reads and deletes one disposable object under `bsnes-jg/_validation/`. Review the provider's bucket scope as well: successful object access does not prove least privilege. Account-level setup credentials are separate from publication credentials.

## Candidate preparation

Commit the source changes first. Choose the next Android version name and a version code above every previously reserved/published code. The browser npm version remains independent and is recorded in the candidate.

```sh
task web:release:test
task web:release:prepare VERSION=0.1.10 VERSION_CODE=11
task web:release:preview CANDIDATE="$PWD/.private/release/candidates/0.1.10"
```

Preparation rebuilds the web core, stages the npm payload, checks browser WRAM fidelity and package sync, builds both signed Native APKs, verifies certificate/package/version/ABI/ROM assets and freezes the candidate in `.private/release/candidates/`. The manifest records exact hashes, catalog hash and source inputs. Generated `dist/` changes may appear after preparation; review them separately rather than editing the frozen candidate. Do not modify candidate files to retry a failed gate.

## Publication and recovery

```sh
task web:release CANDIDATE="$PWD/.private/release/candidates/0.1.10"
task web:release:check
```

The command re-inspects the candidate, prints bucket/current/previous/deletion candidates, and asks for `PUBLISH`. It holds a remote lock through upload, manifest commit, alias repair and pruning. Every public APK is downloaded back and hashed before promotion. Only current/previous remain after a successful run. Browser tarballs stay in the candidate for the separate consumer/npm release; they are not uploaded as APKs.

An upload/hash failure leaves the old manifest authoritative. A failure after pointer publication can mean **published but cleanup/alias repair incomplete**; inspect the canonical manifest and remote journal, then resume the *same* candidate:

```sh
task web:release:resume CANDIDATE="$PWD/.private/release/candidates/0.1.10"
```

Journals are under `bsnes-jg/_release/journals/`; the permanent version-code high-water record is under the same control prefix. Neither is in the pruned release prefix. Resume cannot advance previous twice or replace immutable bytes. An unknown object in the release prefix stops pruning for review.

A crashed process can leave `bsnes-jg/_release/lock.json`. Confirm its owner has stopped, inspect its token through the authenticated object client, and use `task web:release:unlock TOKEN=<token>`. There is deliberately no automatic stale-lock expiry that could allow two publishers to overlap. All publishing tools must honor this lock; the manifest also uses a conditional ETag write to reject outside changes.

Changing the download pointer to an older version does not downgrade an installed Android app. Ship a corrective APK with a higher versionCode for an in-place update.

## Device proof and pages

Use only `task chromecast:*` coordinator sessions to install/navigate/capture Cast1 or Pixel. On TV, Share app APK offers **Local transfer QR** and **Public download QR** when the release URL is configured. Public QR points to the stable product entry, includes a readable URL, and does not upload the installed APK. The published release can differ from the sender's app. Quick Share requires a second Android device and real recipient confirmation; a renderer capture is not transfer proof.

The Indri listing implementation reads current/previous through its Worker proxy, validates the manifest and renders both APK variants. Its source changes and the wald3n source listing must be deployed separately before claiming live-page validation. Attach real captures and compact receipts inline in the [release implementation plan](../plans/2026-10-31-repeatable-release-tooling.md).

The remote lock/manifest implementation relies on R2's documented atomic conditional writes: [R2 S3 compatibility](https://developers.cloudflare.com/r2/api/s3/api/). Credential scopes follow [R2 authentication](https://developers.cloudflare.com/r2/api/tokens/).
