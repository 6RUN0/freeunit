# Fork scope

This repository is a **downstream packaging fork** of
[FreeUnit](https://github.com/freeunitorg/freeunit) (itself the community LTS
fork of the archived NGINX Unit). It exists to produce Debian packages and
nothing more.

**Principle: minimal divergence.** The fork tracks upstream `master` and
deliberately avoids patching the C core or any language module source. The only
additions are packaging metadata, CI, and local build tooling. If a source fix
is ever required, it should be kept as small as possible and, where it makes
sense, proposed upstream rather than carried here indefinitely.

## What is built

Debian **trixie** binary packages for the core daemon and a curated set of
language modules:

| Package | Contents |
|---------|----------|
| `unit` | core daemon (njs + OTel, built from `pkg/contrib` + Rust crates) |
| `unit-php8.3` | PHP 8.3 module (from deb.sury.org) |
| `unit-php8.4` | PHP 8.4 module (from deb.sury.org) |
| `unit-php8.5` | PHP 8.5 module (from deb.sury.org) |
| `unit-python3.13` | Python 3.13 module (native trixie) |

The packaging lives in `pkg/deb/` — one `Makefile.<lang><version>` per module,
included from `pkg/deb/Makefile` under the `trixie` codename, following the
upstream packaging convention. The PHP embed SAPI exposes an unversioned
`libphp.so`, so only one PHP version can run in a single instance; each module
is therefore built and smoke-tested independently.

## Building locally

All builds run inside a clean `debian:trixie` container with the source mounted
at `/unit`, mirroring CI:

```bash
./pkg/deb/build-local.sh            # full build + isolated smoke (mirrors CI)
./pkg/deb/build-local.sh -m         # rebuild only the language modules, then smoke
./pkg/deb/build-local.sh -s         # smoke-test the debs already in pkg/deb/debs/
./pkg/deb/build-local.sh -B         # build the debs, skip the smoke test
./pkg/deb/build-local.sh -C         # remove all generated artifacts and exit
./pkg/deb/build-local.sh -h         # full option list
```

Built `.deb` files land in `pkg/deb/debs/`.

## Continuous integration

CI is defined in [`.github/workflows/build-deb.yml`](.github/workflows/build-deb.yml).
It runs three jobs: build the packages, smoke-test each module in its own clean
container, then (on a tag only) attach the `.deb` files to a GitHub Release.

It is triggered by:

- `workflow_dispatch` — manual run;
- a push to the fork development branches (`current`, `stable`, `develop`) —
  produces build artifacts;
- a push of a version tag — additionally publishes the `.deb` files to the
  matching Release. The release job runs only after the smoke tests pass.
  Two tag shapes are accepted: the plain upstream `X.Y.Z`, and the
  fork-specific `X.Y.Z-buildN` (the Nth packaging build on top of upstream
  `X.Y.Z`, e.g. `1.35.5-build1`).

GitHub Actions are pinned to commit SHAs, and the workflow runs with
least-privilege permissions (only the release job elevates to `contents: write`).

## Staying in sync with upstream

To keep merge friction low, upstream files are left untouched wherever possible.
The fork-specific additions are confined to:

- `pkg/deb/` — packaging makefiles, example configs, `build-local.sh`;
- `.github/workflows/build-deb.yml` — the packaging CI;
- the fork banner at the top of `README.md` (a self-contained block above the
  upstream content) and this `FORK.md`.

When pulling from upstream, conflicts should be limited to these paths.

## Where to report issues

Bugs in the application server, language modules, or documentation belong
**upstream** at <https://github.com/freeunitorg/freeunit>. Use this repository's
issue tracker only for problems specific to the Debian packaging or its CI.
