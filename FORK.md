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

If `packages.sury.org` is unreachable, replace it in both the `curl` and the
`URIs:` line with a mirror that also serves the `apt.gpg` key — for example
`https://mirror.yandex.ru/mirrors/packages.sury.org`. See **Mirrors for
restricted or offline builds** below for the verified list and the key checksum.

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

### Mirrors for restricted or offline builds

`SURY_MIRROR` replaces the deb.sury.org base — the signing **key** and the apt
source both — for builds behind a proxy or when upstream `packages.sury.org` is
unreachable. It is read by `pkg/deb/sury-setup.sh`, so it applies both locally
and in CI. Empty (the default) means upstream, so behaviour is unchanged. The
value is the base URL **without** the trailing `/php`; the helper appends
`/php/apt.gpg` (key) and `/php/` (source) and derives the apt pin host from it.

| Form | `SURY_MIRROR` value | Key resolves from |
|------|---------------------|-------------------|
| Upstream (default) | *(empty)* | `https://packages.sury.org/php/apt.gpg` |
| Full reverse-proxy mirror | `https://mirror.example/sury` | `https://mirror.example/sury/php/apt.gpg` |
| apt-cacher-ng pull-through | `http://cache.example:3142/packages.sury.org` | `http://cache.example:3142/packages.sury.org/php/apt.gpg` |

The mirror must serve `/php/apt.gpg` itself, not only `dists/` and `pool/`: a
plain package mirror that omits the key still fails on the key fetch (this is the
common cause of an unreachable `apt.gpg`). A pull-through cache (apt-cacher-ng)
proxies the key like any other GET, so it covers `apt.gpg` too. The fetched key
becomes apt's trust anchor (`Signed-By`), so its transport matters: over an
**http** base the helper **requires** `SURY_KEY_SHA256` and aborts without it
(the key would otherwise be unauthenticated); over an **https** base the pin is
optional and empty keeps the TLS-only trust of the upstream default.

The apt source pin (`Pin: origin <host>`, which forces PHP to resolve from one
source) is keyed on the URL host. Under a pull-through cache the host collapses
to the cache itself — and if the Debian archive is proxied through the same cache,
the pin no longer isolates Surý from it, so php8.4 (the one line trixie also ships)
may resolve from either side; php8.3/8.5 are Surý-only and unaffected. Prefer a
reverse-proxy mirror on a dedicated host when that determinism matters.

**Known mirrors.** Surý runs no official mirror network — the canonical source is
`packages.sury.org` (CDN-fronted). A few community rsync mirrors carry the full
tree *including* the `apt.gpg` key, so they drop straight into `SURY_MIRROR` when
upstream is down. Verified full mirrors (community-run, not endorsed — re-verify
the host and key before relying on one):

| Mirror | `SURY_MIRROR` value |
|--------|---------------------|
| Yandex (RU) | `https://mirror.yandex.ru/mirrors/packages.sury.org` |
| MPI-Inf (DE) | `https://ftp.mpi-inf.mpg.de/mirrors/linux/mirror/deb.sury.org/repositories` |

Both mirrors serve the same canonical signing key as upstream (OpenPGP RSA-3072,
created 2019-03-18), so a single integrity pin covers all three sources:

```text
SURY_KEY_SHA256=b486fd5488185c4c46467960fa69c53d5085fec492cf76b9eaf3db33561c9d7c
```

Cross-check this sha256 against upstream once `packages.sury.org` is reachable
again.

Locally, pass them on the command line:

```bash
SURY_MIRROR=http://cache.example:3142/packages.sury.org \
SURY_KEY_SHA256=<sha256> ./pkg/deb/build-local.sh
```

In CI both are exposed as `workflow_dispatch` inputs (`sury_mirror`,
`sury_key_sha256`); push triggers leave them empty and build against upstream.
`build-local.sh` additionally honours `DEB_MIRROR`, `CARGO_MIRROR`, and the
`RUSTUP_*` knobs (see its `-h` header) — but those apply to the **local runner
only**: CI does not source `mirror-setup.sh` and installs Rust directly, so it
ignores them.

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
  produces build artifacts. These snapshot builds are versioned
  `X.Y.Z+git<commit-date>.<short-hash>` (computed by `pkg/deb/pkg-version.sh`
  from the built commit of this repository — source and packaging alike), so
  any change yields a new apt-orderable version above the last `X.Y.Z`
  release; the former `X.Y.Z-buildN` packaging tags are no longer needed and
  no longer trigger the workflow;
- a push of a plain upstream version tag `X.Y.Z` — additionally publishes the
  `.deb` files (versioned `X.Y.Z-1`) to the matching Release. The release job
  runs only after the smoke tests pass.

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
