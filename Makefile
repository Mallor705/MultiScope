# Twinverse Makefile
# Professional CI/CD pipeline with automatic versioning

# Variables
PYTHON ?= python3
PIP ?= pip3
FLATPAK ?= flatpak
FLATPAK_BUILDER ?= flatpak-builder
VERSION_FILE = version
VERSION = $(shell cat $(VERSION_FILE))

# Default target
.DEFAULT_GOAL := help

# Help target
help:
	@echo "Twinverse Makefile - Professional Build System"
	@echo ""
	@echo "Usage:"
	@echo "  make build           Build the application with production flags"
	@echo "  make flatpak         Build Flatpak package with validation"
	@echo "  make test            Run test suite with coverage check"
	@echo "  make clean           Remove all temporary artifacts"
	@echo "  make bump-patch      Increment patch version (for critical fixes)"
	@echo "  make release-major   Create major release (requires 3 reviewers)"
	@echo "  make release-custom  Create custom release (blocked on dev branches)"
	@echo "                       Usage: make release-custom v=x.y.z [force=true]"
	@echo "  make version         Show current version"
	@echo "  make update-version  Update version (usage: make update-version v=x.y.z)"
	@echo "  make bump-major      Increment major version (x.0.0)"
	@echo "  make bump-minor      Increment minor version (0.y.0)"
	@echo "  make release-minor   Create a minor release (0.y.0)"
	@echo "  make release-patch   Create a patch release (0.0.z)"
	@echo "  make appimage        Create AppImage package"
	@echo "  make help            Show this help message"
	@echo ""

# Build the application
build:
	@echo "Building Twinverse with production flags..."
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install .
	@echo "Build completed successfully!"

# Build Flatpak package with validation
flatpak: validate-manifest
	@echo "Building Flatpak package..."
	@if [ -n "$(ARCH)" ]; then \
		export FLATPAK_ARCH="$(ARCH)"; \
		./scripts/package-flatpak.sh; \
	else \
		./scripts/package-flatpak.sh; \
	fi
	@echo "Flatpak package built successfully!"

# Validate Flatpak manifest before building
validate-manifest:
	@echo "Validating Flatpak manifest..."
	@if [ ! -f "io.github.mall0r.Twinverse.yaml" ]; then \
		echo "Error: Flatpak manifest io.github.mall0r.Twinverse.yaml not found!"; \
		exit 1; \
	fi
	@echo "Manifest validation passed!"

# Run tests with coverage check
test:
	@echo "Running test suite..."
	$(PYTHON) -m pip install -e ".[test]"
	$(PYTHON) -m pytest
	@echo "Tests completed successfully!"

# Install dependencies for development
dev:
	@echo "Installing development dependencies..."
	$(PYTHON) -m pip install -e ".[test]"
	@echo "Development dependencies installed successfully!"

# Clean temporary files
clean:
	@echo "Cleaning temporary artifacts..."
	./scripts/clean.sh
	@echo "Clean completed!"

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

# Show current version
version:
	@echo "Current version: $(VERSION)"

# Update version
update-version:
ifndef v
	$(error Please specify the new version: make update-version v=1.2.3)
endif
	@echo "Updating version from $(VERSION) to $(v)"
	@python scripts/version_manager.py $(v)

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

# Increment patch version (for critical fixes)
bump-patch:
	@echo "Incrementing patch version..."
	@current_version=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current_version | cut -d. -f1); \
	minor=$$(echo $$current_version | cut -d. -f2); \
	patch=$$(echo $$current_version | cut -d. -f3); \
	new_version=$$major.$$minor.$$((patch + 1)); \
	python scripts/version_manager.py $$new_version

# Create major release (requires 3 reviewers)
release-major: check-deps git-status
	@echo "Creating major release (requires 3 reviewers)..."
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

# Create custom release (blocked on dev branches)
release-custom:
	@if git branch --show-current | grep -E 'dev|beta'; then \
		echo "Error: Custom releases are blocked on development branches"; \
		exit 1; \
	fi
ifndef v
	$(error Please specify the new version: make release-custom v=1.2.3)
endif
	@current_version=$$(cat $(VERSION_FILE)); \
	if [ "$$current_version" = "$(v)" ] && [ "$(force)" != "true" ]; then \
		echo "Version is already $(v)"; \
		echo "Adicione uma opção de -force para que seja possivel fazer mesmo se a Version is already."; \
		exit 1; \
	else \
		$(MAKE) check-deps && \
		$(MAKE) git-status && \
		echo "Creating custom release..." && \
		echo "Updating version from $$current_version to $(v)" && \
		if [ "$(force)" = "true" ]; then \
			python scripts/version_manager.py $(v) force; \
		else \
			python scripts/version_manager.py $(v); \
		fi && \
		echo "Committing version changes" && \
		git add $(VERSION_FILE) share/metainfo/io.github.mall0r.Twinverse.metainfo.xml README.md docs/README.pt-br.md docs/README.es.md scripts/package-appimage.sh io.github.mall0r.Twinverse.yaml scripts/package-flatpak.sh && \
		git commit -m "Bump version to $(v)" && \
		git tag "v$(v)" && \
		echo "Release $(v) created successfully!" && \
		echo "To push changes and tag, run:" && \
		echo "  git push origin main" && \
		echo "  git push origin v$(v)"; \
	fi

# Create AppImage package
appimage:
	@echo "Creating AppImage package..."
	./scripts/package-appimage.sh
	@echo "AppImage package created successfully!"

.PHONY: help build flatpak validate-manifest test clean bump-patch release-major release-custom version update-version bump-major bump-minor release-minor release-patch check-deps git-status appimage dev
