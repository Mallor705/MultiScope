# Makefile para operações de versionamento e build do MultiScope

# Variáveis
VERSION_FILE = version
VERSION = $(shell cat $(VERSION_FILE))

# Targets principais
.PHONY: help version update-version show-version bump-major bump-minor bump-patch

# Mostrar ajuda
help:
	@echo "MultiScope Makefile - Gerenciamento de versão e build"
	@echo ""
	@echo "Targets disponíveis:"
	@echo "  help              - Mostra esta ajuda"
	@echo "  version           - Mostra a versão atual"
	@echo "  show-version      - Mostra a versão atual (mesmo que 'version')"
	@echo "  update-version    - Atualiza a versão (uso: make update-version NEW_VERSION=1.2.3)"
	@echo "  bump-major        - Incrementa versão major (x.0.0)"
	@echo "  bump-minor        - Incrementa versão minor (0.y.0)"
	@echo "  bump-patch        - Incrementa versão patch (0.0.z)"
	@echo ""
	@echo "Exemplos:"
	@echo "  make version"
	@echo "  make update-version NEW_VERSION=1.2.3"
	@echo "  make bump-patch"

# Mostrar versão atual
version show-version:
	@echo "Versão atual: $(VERSION)"

# Atualizar versão
update-version:
ifndef NEW_VERSION
	$(error Por favor, especifique a nova versão: make update-version NEW_VERSION=1.2.3)
endif
	@echo "Atualizando versão de $(VERSION) para $(NEW_VERSION)"
	@python scripts/version_manager.py $(NEW_VERSION)

# Incrementar versão major
bump-major:
	@echo "Incrementando versão major..."
	@current_version=$$(cat version); \
	major=$$(echo $$current_version | cut -d. -f1); \
	minor=0; \
	patch=0; \
	new_version=$$((major + 1)).$$minor.$$patch; \
	python scripts/version_manager.py $$new_version

# Incrementar versão minor
bump-minor:
	@echo "Incrementando versão minor..."
	@current_version=$$(cat version); \
	major=$$(echo $$current_version | cut -d. -f1); \
	minor=$$(echo $$current_version | cut -d. -f2); \
	patch=0; \
	new_version=$$major.$$((minor + 1)).$$patch; \
	python scripts/version_manager.py $$new_version

# Incrementar versão patch
bump-patch:
	@echo "Incrementando versão patch..."
	@current_version=$$(cat version); \
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
