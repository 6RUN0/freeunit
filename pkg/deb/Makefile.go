MODULES+=		go
MODULE_SUFFIX_go=	go

MODULE_SUMMARY_go=	Go module for $(BRAND_TITLE)

MODULE_VERSION_go=	$(VERSION)
MODULE_RELEASE_go=	1

MODULE_CONFARGS_go=	go --go-path=/usr/share/gocode
MODULE_MAKEARGS_go=	go
MODULE_INSTARGS_go=	go-install-src

MODULE_SOURCES_go=	freeunit.example-go-app \
			freeunit.example-go-config

BUILD_DEPENDS_go=	golang
BUILD_DEPENDS+=		$(BUILD_DEPENDS_go)

MODULE_BUILD_DEPENDS_go=,golang
MODULE_DEPENDS_go=,golang,$(BRAND)-dev (= $(VERSION)-$(RELEASE)~$(CODENAME))

MODULE_NOARCH_go=	true

define MODULE_PREINSTALL_go
	mkdir -p debian/$(BRAND)-go/usr/share/doc/$(BRAND)-go/examples/go-app
	install -m 644 -p debian/freeunit.example-go-app debian/$(BRAND)-go/usr/share/doc/$(BRAND)-go/examples/go-app/let-my-people.go
	install -m 644 -p debian/freeunit.example-go-config debian/$(BRAND)-go/usr/share/doc/$(BRAND)-go/examples/$(BRAND).config
endef
export MODULE_PREINSTALL_go

# The sample-build instructions stage the binary in a private mktemp dir, not
# a predictable /tmp path a local user could swap between `go build` and the
# root `install`. The quoted 'BANNER' delimiter keeps the $-syntax literal at
# install time (backslash-escaping would not survive the sed that splices
# this text into preinst); everything dynamic here is expanded by make.
define MODULE_POST_go
cat <<'BANNER'
----------------------------------------------------------------------

The $(MODULE_SUMMARY_go) has been installed.

To check out the sample app, run these commands:

 d=$$(mktemp -d)
 GOPATH=/usr/share/gocode GO111MODULE=auto go build -o "$$d/go-app" /usr/share/doc/$(BRAND)-$(MODULE_SUFFIX_go)/examples/go-app/let-my-people.go
 sudo install -m 755 "$$d/go-app" /usr/local/bin/$(BRAND)-go-app
 rm -rf "$$d"
 sudo service $(RUNTIME) restart
 cd /usr/share/doc/$(BRAND)-$(MODULE_SUFFIX_go)/examples
 $(MODULE_CONFIG_PUT)
 curl http://localhost:8500/

Online documentation is available at $(DOCS_URL)

----------------------------------------------------------------------
BANNER
endef
export MODULE_POST_go
