# Rename the project to `bsnes-jg-player`

**Status:** In progress.

## Decision

Use **bsnes-jg-player** as the public project and product name. Keep “WebAssembly” as the browser runtime/implementation description, not the product identity. The npm package remains `@wbniv/bsnes-jg-player`; the APK download prefix remains `https://downloads.biohack.net/bsnes-jg/` because it is an established binary-delivery path.

## Rename scope

- Rename the GitHub repository from `wbniv/bsnes-jg-wasm` to `wbniv/bsnes-jg-player` and update its local checkout directory and `origin` remote.
- Use `https://indri.studio/apps/bsnes-jg-player/` as the canonical product page. Do not preserve or redirect the old `/apps/bsnes-jg-wasm/` product-page route. Update the Indri page source, its navigation/canonical metadata, and links in the Indri home page.
- Update this repository’s current README, package repository metadata, integration guide, current release manifests, and live links to the new GitHub and product-page URLs.
- Keep historical plans, archived release provenance, `.history`, prior commit links, and artifact filenames as records of what existed at the time. GitHub repository redirects preserve old links after the repository rename.
- Update dependent repositories’ Git URL dependencies and deployment/configuration references where they use the old repository URL. npm consumers continue using `@wbniv/bsnes-jg-player` and need no package rename.

## Migration order

1. Update the current-source metadata and live documentation in this repository.
2. Rename the GitHub repository; confirm the old GitHub URL redirects and update `origin`.
3. Move the local checkout directory to `/home/will/bsnes-jg-player` and resume work from that path.
4. Update the Indri site to serve the new canonical product URL; let the old product-page route become unavailable.
5. Find and update remaining live Git URL dependencies outside this repository, then build/check consumers.

## Acceptance checks

- `git remote -v` points at `wbniv/bsnes-jg-player` from the renamed checkout.
- The renamed checkout builds and the npm package still installs as `@wbniv/bsnes-jg-player`.
- The new Indri URL loads the product page; the old Indri product-page route does not redirect.
- Old GitHub links redirect to the renamed repository.
- Stable APK links under `downloads.biohack.net/bsnes-jg/` still work.
- Current release manifests identify the renamed source repository; historical records remain intact.
