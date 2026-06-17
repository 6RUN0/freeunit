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

Debian **trixie** binary packages (`amd64` only) for the core daemon and a
curated set of language modules:

| Package | Contents |
|---------|----------|
| `freeunit` | core daemon with njs and OTel |
| `freeunit-php8.3` | PHP 8.3 module (runtime from deb.sury.org) |
| `freeunit-php8.4` | PHP 8.4 module (runtime native to trixie) |
| `freeunit-php8.5` | PHP 8.5 module (runtime from deb.sury.org) |
| `freeunit-python3.13` | Python 3.13 module (native trixie) |

The package set is brand-named `freeunit` (daemon binary `freeunitd`, control
socket `control.freeunit.sock`, systemd unit `freeunit.service`); the underlying
server still reports itself as `Unit` in its `Server:` header, preserving the
upstream lineage. The brand is a packaging knob (`BRAND`/`RUNTIME` in
`pkg/deb/Makefile`), so a differently-branded set can be produced from the same
tree.

The packaging lives in `pkg/deb/` — one `Makefile.<lang><version>` per module,
included from `pkg/deb/Makefile` under the `trixie` codename, following the
upstream packaging convention. Each `freeunit-phpX.Y` package bundles its own PHP
embed runtime (`libphpX.Y-embed`), and running several PHP embed runtimes in one
server instance is unsupported, so each module is built and smoke-tested
independently — one PHP version per instance.

**Where PHP comes from.** Debian trixie ships a single PHP line — **8.4** — in
its main archive, so `freeunit-php8.4` resolves its `libphp8.4-embed` runtime
natively. The 8.3 and 8.5 lines are absent from trixie; those modules depend on
`libphp8.3-embed` / `libphp8.5-embed` from
[deb.sury.org](https://deb.sury.org) — Ondřej Surý's long-standing PHP
packaging, which carries every maintained PHP line in parallel. The build
enables deb.sury.org **only when a requested `libphpX.Y-embed` is absent from
the base apt sources**; that logic lives in one place, `pkg/deb/sury-setup.sh`,
shared by CI and the local build script and tunable with `SURY=auto|on|off`
(default `auto`). When enabled, deb.sury.org is pinned above the Debian archive
so the build resolves every PHP line from one consistent source deterministically
(this only affects 8.4, the line trixie also carries); because each `freeunit-phpX.Y`
declares its runtime dependency by package name without a version, the pin stays
a build-time detail and never changes what users install. On the target host,
deb.sury.org must therefore be enabled before installing the 8.3 or 8.5 module —
`freeunit-php8.4` resolves `libphp8.4-embed` from trixie and needs nothing
extra. The Python 3.13 module uses trixie's native `python3.13` and needs no
extra repository either.

## Installing the packages

The packages are published as assets on each
[GitHub Release](https://github.com/6RUN0/freeunit/releases), alongside a
`SHA256SUMS` file for integrity verification. They target **Debian trixie**
on **amd64** only. Install the core daemon plus exactly one language module —
the PHP embed SAPI allows only one PHP version per instance.

### Enable deb.sury.org (PHP 8.3 / 8.5 only)

The `libphp8.3-embed` / `libphp8.5-embed` runtimes live in deb.sury.org, so
enable it before installing the 8.3 or 8.5 module. **Skip this step for
`php8.4`** (native to trixie) **or the Python module.** Trixie uses the deb822
`.sources` format:

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg lsb-release
sudo curl -fsSL https://packages.sury.org/php/apt.gpg \
  -o /usr/share/keyrings/sury-php.gpg
sudo tee /etc/apt/sources.list.d/sury-php.sources >/dev/null <<EOF
Types: deb
URIs: https://packages.sury.org/php/
Suites: $(lsb_release -sc)
Components: main
Signed-By: /usr/share/keyrings/sury-php.gpg
EOF
sudo apt-get update
```

### Download, verify, and install

The snippet below resolves the latest release automatically, reads the
package version from `SHA256SUMS`, verifies the downloads, then lets apt pull
the runtime dependencies (`libphpX.Y-embed` — native trixie for 8.4, sury for
8.3/8.5). Pick one module via `MOD`:

```bash
REPO=6RUN0/freeunit
MOD=php8.4   # php8.3 | php8.4 | php8.5 | python3.13

TAG=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" \
  | sed -nE 's/.*"tag_name":[[:space:]]*"([^"]+)".*/\1/p')
BASE="https://github.com/$REPO/releases/download/$TAG"

curl -fLO "$BASE/SHA256SUMS"
# The .deb asset names embed the package version; read it from SHA256SUMS:
DEB=$(sed -nE 's/^[0-9a-f]+  freeunit_(.+)_amd64\.deb$/\1/p' SHA256SUMS)
curl -fLO "$BASE/freeunit_${DEB}_amd64.deb"
curl -fLO "$BASE/freeunit-${MOD}_${DEB}_amd64.deb"

sha256sum -c --ignore-missing SHA256SUMS
sudo apt-get install -y \
  "./freeunit_${DEB}_amd64.deb" "./freeunit-${MOD}_${DEB}_amd64.deb"
```

`sha256sum -c --ignore-missing` checks only the files you downloaded and
fails if any digest does not match; it covers integrity, not authenticity.
The asset file names use `X.Y.Z-1.trixie` while the installed package version
is `X.Y.Z-1~trixie` (GitHub renders `~` as `.` in asset names). Optional
`-dbg` and `-dev` packages are attached to the same release.

### Run and verify

The package ships a systemd unit (and a sysvinit script). Start and enable
the daemon, then confirm the control API answers:

```bash
sudo systemctl enable --now freeunit
systemctl status freeunit
sudo curl --unix-socket /var/run/control.freeunit.sock http://localhost/
```

Operator paths: control socket `/var/run/control.freeunit.sock`, log
`/var/log/freeunit.log`, pid `/var/run/freeunit.pid`. An example configuration
ships at `/usr/share/doc/freeunit/examples/example.config` as a starting point;
for full configuration see upstream.

### Uninstall

```bash
sudo apt-get remove freeunit    # remove binaries, keep config
sudo apt-get purge freeunit     # remove everything, including config and logs
```

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

These are the common flags; `-h` prints the full list (including `-n`
dry-run and `-I` image override). The `SURY=auto|on|off` environment variable
controls deb.sury.org enablement via the shared `pkg/deb/sury-setup.sh` helper,
exactly as CI does. Built `.deb` files land in `pkg/deb/debs/`.

## Continuous integration

CI is defined in [`.github/workflows/build-deb.yml`](.github/workflows/build-deb.yml).
It runs four jobs: `build-trixie` builds the packages; `smoke-test` installs and
exercises each module in its own clean container (config round-trip, a served
request, and a clean-shutdown assertion); `package-qa` runs the shared package-QA
gates (control-field + lintian checks, install/remove/purge lifecycle, and a
drop-in upgrade over a synthetic upstream `unit` package); then `release` (on a
tag only) attaches the `.deb` files to a GitHub Release. The smoke-test and
package-QA gates are shared verbatim with the local runner via
`pkg/deb/smoke-asserts.sh` and `pkg/deb/pkg-qa.sh`, so CI and `build-local.sh`
assert exactly the same things.

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

- `pkg/deb/` — packaging makefiles, example configs, `build-local.sh`, the
  shared `sury-setup.sh` helper;
- `.github/workflows/build-deb.yml` — the packaging CI;
- the fork banner at the top of `README.md` (a self-contained block above the
  upstream content) and this `FORK.md`.

When pulling from upstream, conflicts should be limited to these paths.

## Where to report issues

Bugs in the application server, language modules, or documentation belong
**upstream** at <https://github.com/freeunitorg/freeunit>. Use this repository's
issue tracker only for problems specific to the Debian packaging or its CI.
