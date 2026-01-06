# Makefile para operações de versionamento e build do MultiScope

# Variáveis
VERSION_FILE = version
VERSION = $(shell cat $(VERSION_FILE))

# Targets principais
.PHONY: help version update-version bump-major bump-minor bump-patch release-major release-minor release-patch release-custom check-deps git-status

# Mostrar ajuda
help:
	@echo "MultiScope Makefile - Gerenciamento de versão e build"
	@echo ""
	@echo "Targets disponíveis:"
	@echo "  help              - Mostra esta ajuda"
	@echo "  version           - Mostra a versão atual"
	@echo "  update-version    - Atualiza a versão (uso: make update-version NEW_VERSION=1.2.3)"
	@echo "  bump-major        - Incrementa versão major (x.0.0)"
	@echo "  bump-minor        - Incrementa versão minor (0.y.0)"
	@echo "  bump-patch        - Incrementa versão patch (0.0.z)"
	@echo "  release-major     - Cria uma release major (x.0.0)"
	@echo "  release-minor     - Cria uma release minor (0.y.0)"
	@echo "  release-patch     - Cria uma release patch (0.0.z)"
	@echo "  release-custom    - Cria uma release customizada (uso: make release-custom NEW_VERSION=1.2.3)"
	@echo "  check-deps        - Verifica as dependências necessárias"
	@echo "  git-status        - Verifica o status do repositório git"
	@echo ""
	@echo "Exemplos:"
	@echo "  make version"
	@echo "  make update-version NEW_VERSION=1.2.3"
	@echo "  make bump-patch"
	@echo "  make release-major"
	@echo "  make release-custom NEW_VERSION=2.1.5"

# Mostrar versão atual
version:
	@echo "Versão atual: $(VERSION)"

# Verificar dependências
check-deps:
	@echo "Verificando dependências..."
	@command -v git >/dev/null 2>&1 || { echo "Erro: git não encontrado"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "Erro: python3 não encontrado"; exit 1; }
	@if [ ! -d ".git" ]; then echo "Erro: Não está em um repositório git"; exit 1; fi
	@echo "Todas as dependências estão presentes"

# Verificar status do git
git-status:
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Há alterações não commitadas no repositório"; \
		git status --porcelain; \
		exit 1; \
	else \
		echo "Repositório git limpo"; \
	fi

# Atualizar versão
update-version:
ifndef NEW_VERSION
	$(error Por favor, especifique a nova versão: make update-version NEW_VERSION=1.2.3)
endif
	@echo "Atualizando versão de $(VERSION) para $(NEW_VERSION)"
	@python scripts/version_manager.py $(NEW_VERSION)

# Criar release major
release-major: check-deps git-status
	@echo "Criando release major..."
	@current_version=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current_version | cut -d. -f1); \
	minor=$$(echo $$current_version | cut -d. -f2); \
	patch=$$(echo $$current_version | cut -d. -f3); \
	new_version=$$((major + 1)).0.0; \
	echo "Atualizando versão de $$current_version para $$new_version"; \
	python scripts/version_manager.py $$new_version; \
	echo "Fazendo commit das alterações de versionamento"; \
	git add $(VERSION_FILE) share/metainfo/io.github.mallor.MultiScope.metainfo.xml README.md docs/README.pt-br.md docs/README.es.md scripts/package-appimage.sh io.github.mallor.MultiScope.yaml scripts/package-flatpak.sh; \
	git commit -m "Bump version to $$new_version"; \
	git tag "v$$new_version"; \
	echo "Release $$new_version criada com sucesso!"; \
	echo "Para fazer push das alterações e da tag, execute:"; \
	echo "  git push origin main"; \
	echo "  git push origin v$$new_version"

# Criar release minor
release-minor: check-deps git-status
	@echo "Criando release minor..."
	@current_version=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current_version | cut -d. -f1); \
	minor=$$(echo $$current_version | cut -d. -f2); \
	patch=$$(echo $$current_version | cut -d. -f3); \
	new_version=$$major.$$((minor + 1)).0; \
	echo "Atualizando versão de $$current_version para $$new_version"; \
	python scripts/version_manager.py $$new_version; \
	echo "Fazendo commit das alterações de versionamento"; \
	git add $(VERSION_FILE) share/metainfo/io.github.mallor.MultiScope.metainfo.xml README.md docs/README.pt-br.md docs/README.es.md scripts/package-appimage.sh io.github.mallor.MultiScope.yaml scripts/package-flatpak.sh; \
	git commit -m "Bump version to $$new_version"; \
	git tag "v$$new_version"; \
	echo "Release $$new_version criada com sucesso!"; \
	echo "Para fazer push das alterações e da tag, execute:"; \
	echo "  git push origin main"; \
	echo "  git push origin v$$new_version"

# Criar release patch
release-patch: check-deps git-status
	@echo "Criando release patch..."
	@current_version=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current_version | cut -d. -f1); \
	minor=$$(echo $$current_version | cut -d. -f2); \
	patch=$$(echo $$current_version | cut -d. -f3); \
	new_version=$$major.$$minor.$$((patch + 1)); \
	echo "Atualizando versão de $$current_version para $$new_version"; \
	python scripts/version_manager.py $$new_version; \
	echo "Fazendo commit das alterações de versionamento"; \
	git add $(VERSION_FILE) share/metainfo/io.github.mallor.MultiScope.metainfo.xml README.md docs/README.pt-br.md docs/README.es.md scripts/package-appimage.sh io.github.mallor.MultiScope.yaml scripts/package-flatpak.sh; \
	git commit -m "Bump version to $$new_version"; \
	git tag "v$$new_version"; \
	echo "Release $$new_version criada com sucesso!"; \
	echo "Para fazer push das alterações e da tag, execute:"; \
	echo "  git push origin main"; \
	echo "  git push origin v$$new_version"

# Criar release customizada
release-custom:
ifndef NEW_VERSION
	$(error Por favor, especifique a nova versão: make release-custom NEW_VERSION=1.2.3)
endif
	@current_version=$$(cat $(VERSION_FILE)); \
	if [ "$$current_version" = "$(NEW_VERSION)" ]; then \
		echo "A versão já é $(NEW_VERSION)"; \
	else \
		$(MAKE) check-deps; \
		$(MAKE) git-status; \
		echo "Criando release customizada..."; \
		echo "Atualizando versão de $$current_version para $(NEW_VERSION)"; \
		python scripts/version_manager.py $(NEW_VERSION); \
		echo "Fazendo commit das alterações de versionamento"; \
		git add $(VERSION_FILE) share/metainfo/io.github.mallor.MultiScope.metainfo.xml README.md docs/README.pt-br.md docs/README.es.md scripts/package-appimage.sh io.github.mallor.MultiScope.yaml scripts/package-flatpak.sh; \
		git commit -m "Bump version to $(NEW_VERSION)"; \
		git tag "v$(NEW_VERSION)"; \
		echo "Release $(NEW_VERSION) criada com sucesso!"; \
		echo "Para fazer push das alterações e da tag, execute:"; \
		echo "  git push origin main"; \
		echo "  git push origin v$(NEW_VERSION)"; \
	fi

# Incrementar versão major
bump-major:
	@echo "Incrementando versão major..."
	@current_version=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current_version | cut -d. -f1); \
	minor=0; \
	patch=0; \
	new_version=$$((major + 1)).$$minor.$$patch; \
	python scripts/version_manager.py $$new_version

# Incrementar versão minor
bump-minor:
	@echo "Incrementando versão minor..."
	@current_version=$$(cat $(VERSION_FILE)); \
	major=$$(echo $$current_version | cut -d. -f1); \
	minor=$$(echo $$current_version | cut -d. -f2); \
	patch=0; \
	new_version=$$major.$$((minor + 1)).$$patch; \
	python scripts/version_manager.py $$new_version

# Incrementar versão patch
bump-patch:
	@echo "Incrementando versão patch..."
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
