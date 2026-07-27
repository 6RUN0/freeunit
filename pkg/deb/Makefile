#!/usr/bin/make

include ../../version

DEFAULT_VERSION := $(NXT_VERSION)
DEFAULT_RELEASE := 1

VERSION ?= $(DEFAULT_VERSION)
RELEASE ?= $(DEFAULT_RELEASE)

# BRAND   — our package identity in dpkg/apt (Source/Package names, module names).
# RUNTIME — on-disk artifact naming: daemon binary ($(RUNTIME)d), state/log/pid
#           paths, control socket, unix user/group, systemd unit, and the
#           internal module-coupling virtual package ($(RUNTIME)-r<ver>).
# Defaults give a full rebrand (freeunitd, /var/lib/freeunit, the
# control.freeunit.sock socket, /usr/lib/freeunit/modules, the "freeunit"
# user/group and systemd unit) — the fork's own on-disk identity, still without
# touching src/. The rebrand covers the daemon and its state paths only; the
# libunit toolchain keeps upstream-stable names by design, so the unitc/setup-
# unit tools, the unitd.8 man page, the /usr/include/unit headers, libunit*
# libraries, and the compiled-in "Unit/" strings all stay "unit".
# Build a drop-in *replacement* for a stock "unit" install with
# RUNTIME=unit RUNDIR=/var/run: freeunit then adopts that runtime's config dir,
# socket path and systemd unit name so existing configs and automation keep
# working after the swap. This is a replacement, not coexistence: the packages
# declare Conflicts/Replaces against "unit" (see debian/control.in), so freeunit
# and upstream "unit" are never installed side by side.
BRAND   ?= freeunit
RUNTIME ?= freeunit
# BRAND_TITLE — human-readable product name for display strings (systemd unit
#               Description, init headers, install banners). dpkg/path names use
#               BRAND/RUNTIME; this is the prose label a user sees.
BRAND_TITLE ?= FreeUnit
# RUNDIR  — volatile runtime state dir for the control socket and pid file.
#           /var/run keeps the legacy socket location (a symlink to /run); set
#           RUNDIR=/run for the pure FHS path.
# HOMEPAGE — control "Homepage:" field. DOCS_URL — documentation URL shown in
#           the install banners. Both default to the fork; override to retarget.
RUNDIR   ?= /var/run
HOMEPAGE ?= https://freeunit.org
DOCS_URL ?= https://docs.freeunit.org

PACKAGE_VENDOR = FreeUnit Packaging <team@freeunit.org>

SRCDIR=	$(BRAND)-$(VERSION)

CODENAME = $(shell lsb_release -cs)

BUILD_DEPENDS_unit = build-essential debhelper devscripts fakeroot libxml2-utils lintian lsb-release xsltproc libssl-dev libpcre2-dev pkg-config clang llvm cargo rustc
BUILD_DEPENDS = $(BUILD_DEPENDS_unit)

MODULES=

# Shared install-banner command: PUT the module's example config over the
# control socket. Defined once here so the per-language Makefile.* banners stay
# in sync; the example config is installed as $(BRAND).config by the
# MODULE_PREINSTALL_* recipes, so the filename must track $(BRAND).
MODULE_CONFIG_PUT = sudo curl -X PUT --data-binary @$(BRAND).config --unix-socket $(RUNDIR)/control.$(RUNTIME).sock http://localhost/config

# Ubuntu 24.04
ifeq ($(CODENAME),noble)
include Makefile.php
include Makefile.python312
include Makefile.go
include Makefile.perl
include Makefile.ruby
include Makefile.jsc-common
include Makefile.jsc11
include Makefile.jsc17
include Makefile.jsc21
include Makefile.wasm
endif

# Ubuntu 23.10
ifeq ($(CODENAME),mantic)
include Makefile.php
include Makefile.python311
include Makefile.python312
include Makefile.go
include Makefile.perl
include Makefile.ruby
include Makefile.jsc-common
include Makefile.jsc11
include Makefile.jsc17
include Makefile.jsc19
include Makefile.jsc20
include Makefile.jsc21
include Makefile.wasm
endif

# Ubuntu 22.04
ifeq ($(CODENAME),jammy)
include Makefile.php
include Makefile.python27
include Makefile.python310
include Makefile.go
include Makefile.perl
include Makefile.ruby
include Makefile.jsc-common
include Makefile.jsc11
include Makefile.jsc17
include Makefile.jsc18
include Makefile.wasm
endif

# Ubuntu 20.04
ifeq ($(CODENAME),focal)
include Makefile.php
include Makefile.python27
include Makefile.python38
include Makefile.go
include Makefile.perl
include Makefile.ruby
include Makefile.jsc-common
include Makefile.jsc11
include Makefile.wasm
endif

# Debian 13
ifeq ($(CODENAME),trixie)
include Makefile.php
include Makefile.php83
include Makefile.php84
include Makefile.php85
include Makefile.python312
include Makefile.python313
include Makefile.go
include Makefile.perl
include Makefile.ruby
include Makefile.jsc-common
include Makefile.jsc17
include Makefile.jsc21
include Makefile.wasm
endif

# Debian 12
ifeq ($(CODENAME),bookworm)
include Makefile.php
include Makefile.python311
include Makefile.go
include Makefile.perl
include Makefile.ruby
include Makefile.jsc-common
include Makefile.jsc17
include Makefile.wasm
endif

# Debian 11
ifeq ($(CODENAME),bullseye)
include Makefile.php
include Makefile.python27
include Makefile.python39
include Makefile.go
include Makefile.perl
include Makefile.ruby
include Makefile.jsc-common
include Makefile.jsc11
include Makefile.wasm
endif

CONFIGURE_ARGS_COMMON=\
	--prefix=/usr \
	--statedir=/var/lib/$(RUNTIME) \
	--control="unix:$(RUNDIR)/control.$(RUNTIME).sock" \
	--runstatedir=$(RUNDIR) \
	--pid=$(RUNDIR)/$(RUNTIME).pid \
	--logdir=/var/log \
	--log=/var/log/$(RUNTIME).log \
	--tmpdir=/var/tmp \
	--user=$(RUNTIME) \
	--group=$(RUNTIME) \
	--tests \
	--openssl

CONFIGURE_ARGS=\
	$(CONFIGURE_ARGS_COMMON) \
	--njs \
	--otel

export CR=\\n

default:
	@echo "valid targets: all modules unit $(addprefix unit-, $(MODULES)) test test-debug clean"

all: check-build-depends-all unit modules

modules: $(addprefix unit-, $(MODULES))

check-build-depends-%:
	@{ \
	case "$*" in \
		all) pkgs="$(BUILD_DEPENDS)" ;; \
		unit) pkgs="$(BUILD_DEPENDS_unit)" ;; \
		*) pkgs="$(BUILD_DEPENDS_unit) $(BUILD_DEPENDS_$*)" ;; \
	esac ; \
	not_installed= ; \
	for pkg in $${pkgs}; do \
		i=$$(dpkg-query -f '$${db:Status-Status}' -W $${pkg}:$$(dpkg --print-architecture) 2>/dev/null) ; \
		if [ $$? -ne 0 -o "$${i}" != "installed" ]; then \
			i=$$(dpkg-query -f '$${db:Status-Status}' -W $${pkg}:all 2>/dev/null) ; \
			if [ $$? -ne 0 -o "$${i}" != "installed" ]; then \
				not_installed="$${not_installed} $${pkg}" ; \
			fi; \
		fi ; \
	done ; \
	if test -n "$${not_installed}" ; then \
		echo "" >&2 ; \
		echo "The following packages are required in order to proceed:" >&2 ; \
		echo "" >&2 ; \
		echo $${not_installed} >&2 ; \
		echo "" >&2 ; \
		exit 1 ; \
	fi \
	}
	touch $@

# Content stamp for every value substituted into the debian/ templates: the
# recipe rewrites the file only when the value set changes, so a RELEASE/
# CODENAME/RUNTIME switch re-instantiates the trees below — mtime comparison
# alone cannot see a variable change.
PKG_IDENTITY = $(VERSION) $(RELEASE) $(BRAND) $(RUNTIME) $(RUNDIR) $(BRAND_TITLE) $(HOMEPAGE) $(DOCS_URL) $(PACKAGE_VENDOR) $(CODENAME)

debuild/.pkg-identity: FORCE
	@mkdir -p debuild
	@echo "$(PKG_IDENTITY)" | cmp -s - $@ || echo "$(PKG_IDENTITY)" > $@

FORCE:

# Siblings from previous differently-versioned builds are never reused: drop
# them so -k reruns do not accumulate trees and stale artifacts. A separate
# stamp (not part of .debian-stamp) so the module path — which needs the orig
# tarball but not the core debian/ tree — can trigger the prune without
# re-instantiating (and thereby wiping) the core build trees under debian/.
debuild/.prune-stamp: debuild/.pkg-identity
	find debuild -mindepth 1 -maxdepth 1 -type d ! -name '$(SRCDIR)' -exec rm -rf {} +
	find debuild -maxdepth 1 -type f ! -name '.*' ! -name '$(BRAND)*_$(VERSION)[.-]*' -delete
	touch $@

# The stamp file (not the directory) is the target: an interrupted recipe
# leaves no fresh stamp, so the next run re-enters and the leading rm -rf
# heals the partial tree, whereas a directory target would count as made
# forever. The template files, this Makefile with its includes
# ($(MAKEFILE_LIST) — the substituted MODULE_*/CONFIGURE_ARGS values live
# there) and the identity stamp are real prerequisites, so editing any of
# them or switching RELEASE/CODENAME/RUNTIME re-instantiates the tree.
debuild/$(SRCDIR)/.debian-stamp: $(wildcard debian/*) $(MAKEFILE_LIST) debuild/.pkg-identity
	@{ \
	set -e ; \
	rm -rf debuild/$(SRCDIR)/debian ; \
	mkdir -p debuild/$(SRCDIR) ; \
	cp -pr debian debuild/$(SRCDIR) ; \
	D=debuild/$(SRCDIR)/debian ; \
	echo '12' > $$D/compat ; \
	mkdir -p $$D/source ; \
	echo '3.0 (quilt)' > $$D/source/format ; \
	cat debian/control.in | sed \
		-e "s#%%PACKAGE%%#$(BRAND)#g" \
		-e "s#%%RUNTIME%%#$(RUNTIME)#g" \
		-e "s#%%HOMEPAGE%%#$(HOMEPAGE)#g" \
		-e "s#%%PACKAGE_VENDOR%%#$(PACKAGE_VENDOR)#g" \
		-e "s#%%UNIT_VERSION%%#$(VERSION)#g" \
	> $$D/control ; \
	cat debian/rules.in | sed \
		-e "s#%%PACKAGE%%#$(BRAND)#g" \
		-e "s#%%RUNTIME%%#$(RUNTIME)#g" \
		-e "s#%%CONFIGURE_ARGS%%#$(CONFIGURE_ARGS)#g" \
	> $$D/rules ; \
	chmod +x $$D/rules ; \
	[ -f $$D/dirs ] && sed -i -e "s#%%RUNTIME%%#$(RUNTIME)#g" $$D/dirs || true ; \
	[ -f $$D/unit.example.config ] && sed -i -e "s#%%PACKAGE%%#$(BRAND)#g" $$D/unit.example.config || true ; \
	: 'package-scoped helper files: debian/<package>.<ext> (keyed on BRAND)' ; \
	for f in postinst postrm preinst logrotate lintian-overrides ; do \
		s=$$D/freeunit.$$f ; [ -f $$s ] || continue ; \
		sed -i -e "s#%%PACKAGE%%#$(BRAND)#g" -e "s#%%RUNTIME%%#$(RUNTIME)#g" -e "s#%%RUNDIR%%#$(RUNDIR)#g" -e "s#%%DOCS_URL%%#$(DOCS_URL)#g" -e "s#%%BRAND_TITLE%%#$(BRAND_TITLE)#g" $$s ; \
		[ "$(BRAND).$$f" = "freeunit.$$f" ] || mv $$s $$D/$(BRAND).$$f ; \
	done ; \
	: 'init/default are resolved by dh_installinit --name=$(RUNTIME); stage as debian/$(BRAND).$(RUNTIME).<ext> so drop-in mode (RUNTIME != BRAND) finds them' ; \
	for f in init default ; do \
		s=$$D/freeunit.$$f ; [ -f $$s ] || continue ; \
		sed -i -e "s#%%PACKAGE%%#$(BRAND)#g" -e "s#%%RUNTIME%%#$(RUNTIME)#g" -e "s#%%RUNDIR%%#$(RUNDIR)#g" -e "s#%%DOCS_URL%%#$(DOCS_URL)#g" -e "s#%%BRAND_TITLE%%#$(BRAND_TITLE)#g" $$s ; \
		[ "$(BRAND).$(RUNTIME).$$f" = "freeunit.$$f" ] || mv $$s $$D/$(BRAND).$(RUNTIME).$$f ; \
	done ; \
	: 'service templates are named freeunit.unit.service as fixed source placeholders (NOT debhelper <pkg>.<name> form); the loop rewrites them to $(BRAND).$(RUNTIME).service' ; \
	for pair in "freeunit.unit.service $(BRAND).$(RUNTIME).service" \
	            "freeunit.unit-debug.service $(BRAND).$(RUNTIME)-debug.service" ; do \
		set -- $$pair ; s=$$D/$$1 ; d=$$D/$$2 ; [ -f $$s ] || continue ; \
		sed -i -e "s#%%RUNTIME%%#$(RUNTIME)#g" -e "s#%%RUNDIR%%#$(RUNDIR)#g" -e "s#%%BRAND_TITLE%%#$(BRAND_TITLE)#g" $$s ; \
		[ "$$s" = "$$d" ] || mv $$s $$d ; \
	done ; \
	for pair in "freeunit-dev.lintian-overrides $(BRAND)-dev.lintian-overrides" ; do \
		set -- $$pair ; s=$$D/$$1 ; d=$$D/$$2 ; [ -f $$s ] || continue ; \
		sed -i -e "s#%%PACKAGE%%#$(BRAND)#g" -e "s#%%RUNTIME%%#$(RUNTIME)#g" $$s ; \
		[ "$$s" = "$$d" ] || mv $$s $$d ; \
	done ; \
	}
	touch $@

# The topmost changelog entry must carry exactly $(VERSION)-$(RELEASE): dpkg
# forces the upstream part of that version into the .orig tarball name. The
# generated changelog's top entry is whatever changes.xml last recorded for
# this package, which may lag NXT_VERSION, so rewrite it unconditionally
# instead of matching one expected version.
# The .debian-stamp prerequisite is normal (not order-only): re-instantiating
# the debian/ tree removes this file, and the fresh stamp must mark it stale.
debuild/$(SRCDIR)/debian/changelog: ../../docs/changes.xml debuild/$(SRCDIR)/.debian-stamp
	cd ../../docs && make ../build/unit.deb-changelog
	cat ../../build/unit.deb-changelog | sed \
		-e "0,/^unit (/s/^unit ([^~)]*~/unit ($(VERSION)-$(RELEASE)~/" \
		-e "s/^unit (/$(BRAND) (/" \
		-e "s#%%CODENAME%%#$(CODENAME)#g" \
		> $@

# Order-only on the prune stamp: pruning deletes stale top-level files in
# debuild/, so it must not run concurrently with the packing below (-j) —
# the transient $(SRCDIR).tar.gz does not match the keep pattern — yet a
# re-run of the prune does not invalidate the tarball itself.
debuild/$(BRAND)_$(VERSION).orig.tar.gz: | debuild/.prune-stamp
	mkdir -p debuild
	cd ../.. && tar -czf pkg/deb/debuild/$(SRCDIR).tar.gz \
		--transform "s#^#$(SRCDIR)/#" \
		LICENSE NOTICE CHANGES README.md CONTRIBUTING.md configure auto src \
		test tools version go pkg/contrib docs/man/man8/unitd.8.in
	mv debuild/$(SRCDIR).tar.gz debuild/$(BRAND)_$(VERSION).orig.tar.gz

# The unpacked source tree gets its own stamp: a deleted tree (or an
# interrupted extraction) re-extracts even while the tarball itself is up to
# date. When the extraction lived inside the tarball recipe, a missing tree
# never re-ran it and debuild met a tree holding only debian/.
debuild/$(SRCDIR)/.source-stamp: debuild/$(BRAND)_$(VERSION).orig.tar.gz
	cd debuild && tar zxf $(BRAND)_$(VERSION).orig.tar.gz
	touch $@

unit: check-build-depends-unit debuild/$(SRCDIR)/.source-stamp debuild/$(SRCDIR)/debian/changelog
	@echo "===> Building $@ package"
	cd debuild/$(SRCDIR) && debuild --preserve-envvar PATH --preserve-envvar RUSTUP_HOME -us -uc
	mkdir -p debs
# Pin the copy to this build's version: with -k the debuild/ dir may still
# hold artifacts of other versions, and an unpinned copy would republish
# them all into debs/.
	find debuild/ -maxdepth 1 -type f \
		\( -name '$(BRAND)*_$(VERSION)-*' -o -name '$(BRAND)_$(VERSION).orig.tar.gz' \) \
		-exec cp {} debs/ \;
	ln -sfn debuild/$(SRCDIR)/debian/build-unit/build $@

# The stamp file (not the debuild-<mod> directory) is the target, for the
# same reason as .debian-stamp above: an interrupted instantiation must
# re-enter on the next run so the leading rm -rf can heal it. The templates
# and the identity stamp are real prerequisites, so editing debian.module/*
# or switching RELEASE/CODENAME re-instantiates the tree.
debuild-%/.stamp: debuild/$(BRAND)_$(VERSION).orig.tar.gz ../../docs/changes.xml \
		$(wildcard debian.module/*) debian/copyright $(MAKEFILE_LIST) \
		debuild/.pkg-identity
# The directory name carries no version, so a leftover from a previous
# (differently-versioned) build must be dropped, not reused: stale source
# trees, debs and instantiated templates would leak into this build.
	rm -rf debuild-$*
	mkdir debuild-$*
	cp debuild/$(BRAND)_$(VERSION).orig.tar.gz debuild-$*/$(BRAND)-$(MODULE_SUFFIX_$*)_$(VERSION).orig.tar.gz
	cd debuild-$* && tar zxf $(BRAND)-$(MODULE_SUFFIX_$*)_$(VERSION).orig.tar.gz
	mkdir debuild-$*/$(SRCDIR)/debian
	echo '12' > debuild-$*/$(SRCDIR)/debian/compat
	mkdir debuild-$*/$(SRCDIR)/debian/source
	echo '3.0 (quilt)' > debuild-$*/$(SRCDIR)/debian/source/format
	cd ../../docs && make ../build/unit-$(MODULE_SUFFIX_$*).deb-changelog
# Force the top entry to $(VERSION)-$(RELEASE) whatever changes.xml last
# recorded for this module (several lag NXT_VERSION), or dpkg-source will
# look for an .orig tarball named after the stale version and fail.
	cat ../../build/unit-$(MODULE_SUFFIX_$*).deb-changelog | sed \
		-e "0,/^unit-$(MODULE_SUFFIX_$*) (/s/^unit-$(MODULE_SUFFIX_$*) ([^~)]*~/unit-$(MODULE_SUFFIX_$*) ($(VERSION)-$(RELEASE)~/" \
		-e "s/^unit-$(MODULE_SUFFIX_$*) (/$(BRAND)-$(MODULE_SUFFIX_$*) (/" \
		-e "s#%%CODENAME%%#$(CODENAME)#g" \
		> debuild-$*/$(SRCDIR)/debian/changelog
	if [ -f debian.module/copyright.unit-$(MODULE_SUFFIX_$*) ]; then \
		cp debian.module/copyright.unit-$(MODULE_SUFFIX_$*) debuild-$*/$(SRCDIR)/debian/copyright ; \
	else \
		cp debian/copyright debuild-$*/$(SRCDIR)/debian/ ; \
	fi
	@{ \
	set -e ; \
	for src in $(MODULE_SOURCES_$*); do \
		sed -e "s#%%NAME%%#$(BRAND)-$(MODULE_SUFFIX_$*)#g" \
		    -e "s#%%PACKAGE%%#$(BRAND)#g" \
		    -e "s#%%RUNTIME%%#$(RUNTIME)#g" \
		    debian.module/$${src} > debuild-$*/$(SRCDIR)/debian/$${src} ; \
	done ; \
	definitions=`echo "$$MODULE_DEFINITIONS_$*" | sed -e ':a' -e 'N' -e '$$!ba' -e "s/\n/\$$CR/g"` ; \
	prebuild=`echo "$$MODULE_PREBUILD_$*" | sed -e ':a' -e 'N' -e '$$!ba' -e "s/\n/\$$CR/g"` ; \
	preinstall=`echo "$$MODULE_PREINSTALL_$*" | sed -e ':a' -e 'N' -e '$$!ba' -e "s/\n/\$$CR/g"` ; \
	postinstall=`echo "$$MODULE_POSTINSTALL_$*" | sed -e ':a' -e 'N' -e '$$!ba' -e "s/\n/\$$CR/g"` ; \
	post=`echo "$$MODULE_POST_$*" | sed -e ':a' -e 'N' -e '$$!ba' -e "s/\n/\$$CR/g"` ; \
	cat debian.module/$(if $(MODULE_NOARCH_$*),control-noarch.in,control.in) | sed \
                -e "s#%%NAME%%#$(BRAND)-$(MODULE_SUFFIX_$*)#g" \
                -e "s#%%OLDNAME%%#unit-$(MODULE_SUFFIX_$*)#g" \
                -e "s#%%PACKAGE%%#$(BRAND)#g" \
                -e "s#%%RUNTIME%%#$(RUNTIME)#g" \
                -e "s#%%SUMMARY%%#$(MODULE_SUMMARY_$*)#g" \
                -e "s#%%CODENAME%%#$(CODENAME)#g" \
                -e "s#%%UNIT_VERSION%%#$(VERSION)#g" \
                -e "s#%%UNIT_RELEASE%%#$(RELEASE)#g" \
                -e "s#%%VERSION%%#$(MODULE_VERSION_$*)#g" \
                -e "s#%%RELEASE%%#$(MODULE_RELEASE_$*)#g" \
                -e "s#%%HOMEPAGE%%#$(HOMEPAGE)#g" \
                -e "s#%%PACKAGE_VENDOR%%#$(PACKAGE_VENDOR)#g" \
                -e "s#%%MODULE_BUILD_DEPENDS%%#$(MODULE_BUILD_DEPENDS_$*)#g" \
                -e "s#%%MODULE_DEPENDS%%#$(MODULE_DEPENDS_$*)#g" \
        > debuild-$*/$(SRCDIR)/debian/control ; \
        cat debian.module/$(if $(MODULE_NOARCH_$*),rules-noarch.in,rules.in) | sed \
                -e "s#%%NAME%%#$(BRAND)-$(MODULE_SUFFIX_$*)#g" \
                -e "s#%%RUNTIME%%#$(RUNTIME)#g" \
                -e "s#%%CODENAME%%#$(CODENAME)#g" \
                -e "s#%%UNIT_VERSION%%#$(VERSION)#g" \
                -e "s#%%UNIT_RELEASE%%#$(RELEASE)#g" \
                -e "s#%%CONFIGURE_ARGS%%#$(CONFIGURE_ARGS_COMMON)#g" \
                -e "s#%%MODULE_CONFARGS%%#$(MODULE_CONFARGS_$*)#g" \
                -e "s#%%MODULE_MAKEARGS%%#$(MODULE_MAKEARGS_$*)#g" \
                -e "s#%%MODULE_INSTARGS%%#$(MODULE_INSTARGS_$*)#g" \
                -e "s#%%MODULE_DEFINITIONS%%#$${definitions}#g" \
                -e "s#%%MODULE_PREBUILD%%#$${prebuild}#g" \
                -e "s#%%MODULE_PREINSTALL%%#$${preinstall}#g" \
                -e "s#%%MODULE_POSTINSTALL%%#$${postinstall}#g" \
        > debuild-$*/$(SRCDIR)/debian/rules ; \
        cat debian.module/preinst.in | sed \
                -e "s#%%MODULE_POST%%#$$post#g" \
        > debuild-$*/$(SRCDIR)/debian/preinst ; \
        chmod +x debuild-$*/$(SRCDIR)/debian/rules ; \
	}
	touch $@

# The module stamp is a normal (not order-only) prerequisite: its recipe
# re-runs on a version change (fresh orig tarball), and only a normal
# dependency propagates that staleness here — order-only would leave $@ "up
# to date" and silently skip rebuilding the module against the recreated
# source tree.
unit-%: check-build-depends-% debuild-%/.stamp
	@echo "===> Building $@ package"
	cd debuild-$*/$(SRCDIR) && debuild --preserve-envvar PATH --preserve-envvar RUSTUP_HOME -us -uc
	mkdir -p debs
	find debuild-$*/ -maxdepth 1 -type f -exec cp {} debs/ \;
	ln -sfn debuild-$*/$(SRCDIR)/debian/build-unit/build $@
# debuild writes .deb/.changes into debuild-$* AFTER the build tree this
# symlink resolves to was last touched, leaving the prerequisite forever newer
# than the target. touch (following the symlink) restores up-to-date-ness so
# an unchanged rerun is a no-op instead of a full debuild.
	touch $@

test: unit modules
	@{ \
	for so in `find debuild-*/$(SRCDIR)/debian/build-unit/ -type f \( -name "*.so" -o -name "*.jar" \)`; do \
		soname=`basename $${so}` ; \
		test "$${soname}" = "java.unit.so" && continue ; \
		test -h debuild/$(SRCDIR)/debian/build-unit/build/lib/$${soname} || \
		ln -fs `pwd`/$${so} debuild/$(SRCDIR)/debian/build-unit/build/lib/$${soname} ; \
	done ; \
	( cd debuild/$(SRCDIR)/debian/build-unit && env python3 -m pytest --user=nobody $(PYTEST_ARGS) ) ; \
	}

test-debug: unit modules
	@{ \
	for so in `find debuild-*/$(SRCDIR)/debian/build-unit-debug/ -type f \( -name "*.so" -o -name "*.jar" \)`; do \
		soname=`basename $${so}` ; \
		test "$${soname}" = "java.unit.so" && continue ; \
		test -h debuild/$(SRCDIR)/debian/build-unit-debug/build/lib/$${soname} || \
		ln -fs `pwd`/$${so} debuild/$(SRCDIR)/debian/build-unit-debug/build/lib/$${soname} ; \
	done ; \
	( cd debuild/$(SRCDIR)/debian/build-unit-debug && env python3 -m pytest --user=nobody $(PYTEST_ARGS) ) ; \
	}

clean:
	rm -rf debuild debuild-* debs ../../build
	rm -f check-build-depends-*
	find . -maxdepth 1 -type l -delete

.PHONY: default all modules test test-debug clean FORCE

# Half-written file targets (changelogs, stamps, tarballs) must never
# satisfy a later run; make already deletes a changed target on a signal,
# this extends that to recipes failing with a nonzero status.
.DELETE_ON_ERROR:

.SECONDARY: $(addprefix check-build-depends-, $(MODULES)) \
	$(foreach m, $(MODULES), debuild-$(m)/.stamp)
