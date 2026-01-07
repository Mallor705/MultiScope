# Makefile for Twinverse versioning and build operations

# Variables
VERSION_FILE = version
VERSION = $(shell cat $(VERSION_FILE))

# Main targets
.PHONY: help version update-version bump-major bump-minor bump-patch release-major release-minor release-patch release-custom check-deps git-status

# Show help
help:
	@echo "Twinverse Makefile - Version and build management"
	@echo ""
	@echo "Available targets:"
	@echo "  help              - Show this help"
	@echo "  version           - Show current version"
	@echo "  update-version    - Update version (usage: make update-version v=x.y.z)"
	@echo "  bump-major        - Increment major version (x.0.0)"
	@echo "  bump-minor        - Increment minor version (0.y.0)"
	@echo "  bump-patch        - Increment patch version (0.0.z)"
	@echo "  release-major     - Create a major release (x.0.0)"
	@echo "  release-minor     - Create a minor release (0.y.0)"
	@echo "  release-patch     - Create a patch release (0.0.z)"
	@echo "  release-custom    - Create a custom release (usage: make release-custom v=x.y.z)"
	@echo "  check-deps        - Check required dependencies"
	@echo "  git-status        - Check git repository status"
	@echo ""
	@echo "Examples:"
	@echo "  make version"
	@echo "  make update-version v=x.y.z"
	@echo "  make bump-patch"
	@echo "  make release-major"
	@echo "  make release-custom v=x.y.z"

# Show current version
version:
	@echo "Current version: $(VERSION)"

# Check dependencies
check-deps:
	@echo "Checking dependencies..."
	@command -v git >/dev/null 2>&1 || { echo "Error: git not found"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "Error: python3 not found"; exit 1; }
	@if [ ! -d ".git" ]; then echo "Error: Not in a git repository"; exit 1; fi
	@echo "All dependencies are present"

# Check git status
git-status:
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "There are uncommitted changes in the repository"; \
		git status --porcelain; \
		exit 1; \
	else \
		echo "Git repository is clean"; \
	fi

# Update version
update-version:
ifndef v
	$(error Please specify the new version: make update-version v=1.2.3)
endif
	@echo "Updating version from $(VERSION) to $(v)"
	@python scripts/version_manager.py $(v)

# Create major release
release-major: check-deps git-status
	@echo "Creating major release..."
	@current_version=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current_version | cut -d. -f1); \
	minor=$$(echo $$current_version | cut -d. -f2); \
	patch=$$(echo $$current_version | cut -d. -f3); \
	new_version=$$((major + 1)).0.0; \
	echo "Updating version from $$current_version to $$new_version"; \
	python scripts/version_manager.py $$new_version; \
	echo "Committing version changes"; \
	git add $(VERSION_FILE) share/metainfo/io.github.mall0r.Twinverse.metainfo.xml README.md docs/README.pt-br.md docs/README.es.md scripts/package-appimage.sh io.github.mall0r.Twinverse.yaml scripts/package-flatpak.sh; \
	git commit -m "Bump version to $$new_version"; \
	git tag "v$$new_version"; \
	echo "Release $$new_version created successfully!"; \
	echo "To push changes and tag, run:"; \
	echo "  git push origin main"; \
	echo "  git push origin v$$new_version"

# Create minor release
release-minor: check-deps git-status
	@echo "Creating minor release..."
	@current_version=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current_version | cut -d. -f1); \
	minor=$$(echo $$current_version | cut -d. -f2); \
	patch=$$(echo $$current_version | cut -d. -f3); \
	new_version=$$major.$$((minor + 1)).0; \
	echo "Updating version from $$current_version to $$new_version"; \
	python scripts/version_manager.py $$new_version; \
	echo "Committing version changes"; \
	git add $(VERSION_FILE) share/metainfo/io.github.mall0r.Twinverse.metainfo.xml README.md docs/README.pt-br.md docs/README.es.md scripts/package-appimage.sh io.github.mall0r.Twinverse.yaml scripts/package-flatpak.sh; \
	git commit -m "Bump version to $$new_version"; \
	git tag "v$$new_version"; \
	echo "Release $$new_version created successfully!"; \
	echo "To push changes and tag, run:"; \
	echo "  git push origin main"; \
	echo "  git push origin v$$new_version"

# Create patch release
release-patch: check-deps git-status
	@echo "Creating patch release..."
	@current_version=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current_version | cut -d. -f1); \
	minor=$$(echo $$current_version | cut -d. -f2); \
	patch=$$(echo $$current_version | cut -d. -f3); \
	new_version=$$major.$$minor.$$((patch + 1)); \
	echo "Updating version from $$current_version to $$new_version"; \
	python scripts/version_manager.py $$new_version; \
	echo "Committing version changes"; \
	git add $(VERSION_FILE) share/metainfo/io.github.mall0r.Twinverse.metainfo.xml README.md docs/README.pt-br.md docs/README.es.md scripts/package-appimage.sh io.github.mall0r.Twinverse.yaml scripts/package-flatpak.sh; \
	git commit -m "Bump version to $$new_version"; \
	git tag "v$$new_version"; \
	echo "Release $$new_version created successfully!"; \
	echo "To push changes and tag, run:"; \
	echo "  git push origin main"; \
	echo "  git push origin v$$new_version"

# Create custom release
release-custom:
ifndef v
	$(error Please specify the new version: make release-custom v=1.2.3)
endif
	@current_version=$$(cat $(VERSION_FILE)); \
	if [ "$$current_version" = "$(v)" ]; then \
		echo "Version is already $(v)"; \
	else \
		$(MAKE) check-deps && \
		$(MAKE) git-status && \
		echo "Creating custom release..." && \
		echo "Updating version from $$current_version to $(v)" && \
		python scripts/version_manager.py $(v) && \
		echo "Committing version changes" && \
		git add $(VERSION_FILE) share/metainfo/io.github.mall0r.Twinverse.metainfo.xml README.md docs/README.pt-br.md docs/README.es.md scripts/package-appimage.sh io.github.mall0r.Twinverse.yaml scripts/package-flatpak.sh && \
		git commit -m "Bump version to $(v)" && \
		git tag "v$(v)" && \
		echo "Release $(v) created successfully!" && \
		echo "To push changes and tag, run:" && \
		echo "  git push origin main" && \
		echo "  git push origin v$(v)"; \
	fi

# Increment major version
bump-major:
	@echo "Incrementing major version..."
	@current_version=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current_version | cut -d. -f1); \
	minor=0; \
	patch=0; \
	new_version=$$((major + 1)).$$minor.$$patch; \
	python scripts/version_manager.py $$new_version

# Increment minor version
bump-minor:
	@echo "Incrementing minor version..."
	@current_version=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current_version | cut -d. -f1); \
	minor=$$(echo $$current_version | cut -d. -f2); \
	patch=0; \
	new_version=$$major.$$((minor + 1)).$$patch; \
	python scripts/version_manager.py $$new_version

# Increment patch version
bump-patch:
	@echo "Incrementing patch version..."
	@current_version=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current_version | cut -d. -f1); \
	minor=$$(echo $$current_version | cut -d. -f2); \
	patch=$$(echo $$current_version | cut -d. -f3); \
	new_version=$$major.$$minor.$$((patch + 1)); \
	python scripts/version_manager.py $$new_version

# Targets para build e pacotes
.PHONY: build appimage flatpak

build:
	./scripts/build.sh

appimage:
	./scripts/package-appimage.sh

flatpak:
	./scripts/package-flatpak.sh
