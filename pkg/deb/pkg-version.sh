# shellcheck shell=sh
# pkg-version.sh — compute the Debian package version for a FreeUnit build.
#
# Sourced (not executed) by pkg/deb/build-local.sh and the build-deb.yml CI
# workflow, mirroring pkg-qa.sh / smoke-asserts.sh, so both entry points stamp
# identical package versions.
#
# Usage:
#   . ./pkg/deb/pkg-version.sh
#   PKG_VERSION="${PKG_VERSION:-$(pkg_version <repo-root>)}"
#
# Consumes:
#   VERSION            upstream NXT_VERSION — what the daemon reports (1.36.0);
#   PKG_RELEASE_BUILD  non-empty => release build: emit VERSION unchanged.
#
# Snapshot builds (the default) append +git<commit-timestamp>.<short-hash> of
# THIS repository's HEAD — the tree actually built, source and packaging alike
# — so any change, packaging-only included, yields a new apt-orderable version:
#   1.36.0-1  <  1.36.0+git20260727070641.abc12345-1  <  1.36.1-1
# ('+' sorts above the base version, unlike '~'. The full commit timestamp —
# not just the date — orders successive snapshots by commit time down to
# one-second granularity: with a date alone, all same-day builds would sort
# by raw hash and apt would treat roughly half of them as downgrades. Commits
# created within the same second — e.g. a scripted rebase — still fall back
# to hash order.)
# Uncommitted changes to tracked files add a trailing .dirty marker; outside a
# git checkout (a release tarball) the plain VERSION is emitted with a warning.
# Under GitHub Actions the fallback is FATAL instead: CI always builds from a
# checkout, so git failing there means broken version stamping, not a tarball
# build. Container jobs hit exactly that — the workspace stays owned by the
# runner UID while steps run as root, actions/checkout's safe.directory entry
# lives only in a step-temporary git config, and every job degraded to the
# plain VERSION in unison, keeping all version gates green (observed live on
# 2026-07-27: a snapshot prerelease shipped 1.36.0-1 debs).

pkg_version() {
    # shellcheck disable=SC3043  # local: every caller sources this under bash
    local _pv_root _pv_hash _pv_stamp _pv_dirty
    _pv_root="${1:-.}"
    : "${VERSION:?pkg_version: VERSION must be set (NXT_VERSION)}"

    if [ -n "${PKG_RELEASE_BUILD:-}" ]; then
        echo "${VERSION}"
        return 0
    fi

    if ! git -C "${_pv_root}" rev-parse --verify -q HEAD >/dev/null 2>&1; then
        if [ -n "${GITHUB_ACTIONS:-}" ]; then
            echo "pkg-version: git cannot read ${_pv_root} (dubious ownership in a container job?);" >&2
            echo "pkg-version: refusing the plain-VERSION fallback in CI — fix safe.directory in the workflow" >&2
            return 1
        fi
        echo "pkg-version: ${_pv_root} is not a git checkout; using plain ${VERSION}" >&2
        echo "${VERSION}"
        return 0
    fi

    _pv_hash="$(git -C "${_pv_root}" rev-parse --short=8 HEAD)"
    # Commit timestamp (UTC), not wall clock: reproducible for a given commit.
    _pv_stamp="$(TZ=UTC git -C "${_pv_root}" log -1 --format=%cd --date=format-local:%Y%m%d%H%M%S)"
    # Tracked-file changes only (-uno): generated build artifacts and other
    # untracked files must not flip every local rebuild to .dirty.
    _pv_dirty=""
    if [ -n "$(git -C "${_pv_root}" status --porcelain -uno 2>/dev/null)" ]; then
        _pv_dirty=".dirty"
    fi

    echo "${VERSION}+git${_pv_stamp}.${_pv_hash}${_pv_dirty}"
}
