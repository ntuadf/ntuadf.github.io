# NTUADF website

Static website for the National Taiwan University Academic Development Foundation.

## Build and check

Use **Node.js 24+**, **Python 3.11+**, **Hugo 0.170.0**, and **standalone Dart Sass
1.108.2**. Hugo and Sass must be on `PATH`. Hugo no longer needs an extended
edition. No theme submodule checkout is required.

```sh
npm ci --ignore-scripts
npm run build
npm run test:unit
npm run test:site
npx playwright install --with-deps --only-shell chromium
npm run test:browser
```

The Python tests use only the standard library. Cache-purge tests use mock `curl`
and dummy credentials, and the generated-site checker never makes network requests.
Browser tests serve the build on loopback and block external page requests.

## Theme and dependencies

The site now owns its templates and Sass modules; it does not load Bigspring.
The original `themes/bigspring` gitlink is retained for historical reference only.
Its original styling is preserved where used; see `THIRD_PARTY_NOTICES.md`.

- **Bootstrap 5.3.9**, including Popper, replaces Bootstrap 4.
- **jQuery, Slick, Font Awesome, and the remote font loader are no longer loaded.**
- **Lato 400/700** is self-hosted from the locked `@fontsource/lato` package.
  Visitors' existing system fonts remain the fallback for Chinese text.
- Project Sass uses `@use` modules and `sass:color`, with no deprecated `@import`
  or global color functions. Bootstrap's distributed CSS is used directly.
- `package-lock.json` records dependency versions and integrity hashes.
  Dependabot opens weekly npm update PRs and daily Actions update PRs. Update PRs
  must pass the same build and browser checks before deployment.
- Hugo and Dart Sass remain explicitly pinned in the deployment workflow;
  review their release notes and update those pins deliberately.

`node_modules` is not deployed. Hugo mounts only Bootstrap's distributed assets,
the two Lato WOFF2 files, and third-party licenses. npm lifecycle scripts are
disabled during installation.

## Keeping the UI stable

The Sass retains the previous typography, colors, section padding, 30px gutters,
and 1140px maximum desktop container instead of adopting Bootstrap 5's wider
defaults. Navigation uses Bootstrap 5 attributes, with the same menu and icon.

Playwright checks all eight HTML pages on desktop and mobile, including:

- no horizontal overflow, JavaScript errors, or external asset requests;
- menu open/close, keyboard focus, skip links, navigation, and email links;
- container sizes at 320, 768, 1280, and 1440px;
- nine screenshot baselines for the home, board, donation, contact, and open menu.

Screenshots use the locked Chromium version and a locked **test-only** Noto Sans
TC fallback to make Chinese text reproducible across machines. The test font is
served only by `scripts/serve-test-site.mjs`, never included in the public build.
Screenshots allow a 0.5% pixel tolerance for rendering differences.

The November 18, 2026 migration was also compared against a pre-migration source
snapshot: home, board, donation, and contact pages at desktop and mobile sizes.
With controlled fonts, all eight comparisons preserved the measured positions,
dimensions, type sizes, line heights, and colors, and passed screenshot comparison.

For intentional visual changes, review the images before updating baselines:

```sh
npm run build
npm run test:browser:update
```

Do not refresh snapshots merely to silence unexpected failures. CI uploads browser
traces and failed-image comparisons as `browser-diagnostics`.

## Images and accessibility

`static/img` is also mounted under Hugo's `assets/images`. Banners generate 480px,
750px, and 1500px WebP variants with responsive source selection and intrinsic
dimensions. Original files remain available at their existing URLs.

Pages declare Traditional Chinese (`zh-Hant`), use one meaningful primary heading,
and provide a skip link and visible keyboard focus. Automated checks do not replace
human screen-reader testing or visual approval.

## Deployment

Pull requests build and test using a read-only token, without production secrets.
A successful push to `master` uploads the checked site, then a separate
write-enabled job publishes it to `gh-pages` and purges the Cloudflare cache.
No deployment occurs if unit, HTML, browser, or screenshot checks fail.

Repository secrets `CLOUDFLARE_ZONE` and `CLOUDFLARE_TOKEN` must be configured.
Scope the token to cache purge for the intended zone.

The purge script validates HTTP status and JSON `success`, and applies connection
and overall timeouts. It supports optional `PURGE_URLS` as a non-empty JSON array
and legacy global keys through `CLOUDFLARE_KEY` plus `CLOUDFLARE_EMAIL`.
