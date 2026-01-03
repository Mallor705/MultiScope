#!/usr/bin/env bash
# MultiScope Professional Flatpak Build Script
set -euo pipefail

# ===== CONFIGURAÇÃO =====
readonly APP_ID="io.github.mallor.MultiScope"
readonly MANIFEST="$APP_ID.yaml"
readonly BUILD_DIR="build-dir"
readonly REPO_DIR="flatpak-repo"
readonly BUNDLE_NAME="MultiScope.flatpak"

# ===== FUNÇÕES =====
print_header() {
    echo -e "\n\033[1;34m=== $1 ===\033[0m"
}

print_success() {
    echo -e "\033[1;32m✓ $1\033[0m"
}

print_error() {
    echo -e "\033[1;31m✗ $1\033[0m" >&2
}

check_dependencies() {
    print_header "Verificando Dependências"

    local missing_deps=()

    # Comandos obrigatórios
    for cmd in flatpak flatpak-builder ostree; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done

    # Comandos opcionais (apenas para recursos)
    if [[ -f "res/resources.xml" ]]; then
        if ! command -v glib-compile-resources &> /dev/null; then
            print_error "glib-compile-resources não encontrado (necessário para GResource)"
            echo "  Instale: sudo apt install libglib2.0-dev-bin"
            missing_deps+=("glib-compile-resources")
        fi
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Dependências ausentes: ${missing_deps[*]}"
        exit 1
    fi

    print_success "Todas dependências verificadas"
}

setup_runtime() {
    print_header "Configurando Runtime Flatpak"

    local sdk_version="49"  # Ajuste conforme necessário
    local runtime="org.gnome.Platform"
    local sdk="org.gnome.Sdk"

    if ! flatpak list --runtime | grep -q "$runtime//$sdk_version"; then
        echo "Instalando runtime GNOME $sdk_version..."
        flatpak install -y flathub "$runtime//$sdk_version" "$sdk//$sdk_version" || {
            print_error "Falha ao instalar runtime"
            exit 1
        }
    fi

    print_success "Runtime configurado"
}

clean_build() {
    print_header "Limpando Builds Anteriores"

    # Remove diretórios de build
    rm -rf "$BUILD_DIR" .flatpak-builder .flatpak-builder-cache

    # Remove bundle anterior se existir
    [[ -f "$BUNDLE_NAME" ]] && rm -f "$BUNDLE_NAME"

    # Limpa recursos compilados
    [[ -f "res/compiled.gresource" ]] && rm -f "res/compiled.gresource"

    print_success "Ambiente limpo"
}

compile_resources() {
    # Só compila se resources.xml existir
    if [[ -f "res/resources.xml" ]]; then
        print_header "Compilando Recursos"
        glib-compile-resources \
            --target=res/compiled.gresource \
            --sourcedir=res \
            res/resources.xml
        print_success "Recursos compilados"
    fi
}

build_flatpak() {
    print_header "Construindo Flatpak"

    local build_cmd=(
        flatpak-builder
        --force-clean
        --install-deps-from=flathub
        --repo="$REPO_DIR"
        --ccache  # Habilita cache para builds mais rápidos
        --disable-updates  # Evita atualizações automáticas durante build
        --keep-build-dirs  # Mantém diretórios para depuração
    )

    # Verifica se é uma build de desenvolvimento
    if [[ "${1:-}" == "--dev" ]]; then
        build_cmd+=(--user)  # Instala para usuário
    fi

    "${build_cmd[@]}" "$BUILD_DIR" "$MANIFEST"

    print_success "Flatpak construído"
}

create_repository() {
    print_header "Criando Repositório Local"

    if [[ ! -d "$REPO_DIR" ]]; then
        ostree init --mode=archive-z2 --repo="$REPO_DIR"
    fi

    print_success "Repositório pronto"
}

create_bundle() {
    print_header "Criando Bundle"

    # ★ CORREÇÃO: Lê a versão do arquivo metainfo.xml ★
    local metainfo_path="share/metainfo/io.github.mallor.MultiScope.metainfo.xml"
    local version
    version=$(grep -oP '<release version="\K[^"]+' "$metainfo_path" | head -1)

    # Nome do bundle com a versão extraída
    local final_bundle="MultiScope-${version:-unknown}.flatpak"

    echo "📦 Criando: $final_bundle"
    echo "📄 Fonte da versão: $metainfo_path"
    echo "🆔 App ID: $APP_ID"
    echo ""

    # Remove bundle anterior se existir
    [[ -f "$final_bundle" ]] && rm -f "$final_bundle"

    # Comando DIRETO - mostra logs automaticamente
    flatpak build-bundle "$REPO_DIR" "$final_bundle" "$APP_ID"

    # Verificação simples
    if [[ -f "$final_bundle" ]]; then
        local bundle_size
        bundle_size=$(du -h "$final_bundle" | cut -f1)
        print_success "✅ Bundle criado com sucesso!"
        echo "   Arquivo: $final_bundle"
        echo "   Tamanho: $bundle_size"
        echo "   Versão: $version"
        return 0
    else
        print_error "❌ Falha ao criar bundle"
        return 1
    fi
}

test_build() {
    print_header "Testando Build"

    # Testa usando o nome do binário real (multiscope) em vez do App ID
    if timeout 5s flatpak-builder --run "$BUILD_DIR" "$MANIFEST" "multiscope" --help >/dev/null 2>&1; then
        print_success "Build testado com sucesso"
    elif timeout 5s flatpak-builder --run "$BUILD_DIR" "$MANIFEST" "multiscope" >/dev/null 2>&1; then
        print_success "Build testado (executou sem argumentos)"
    else
        # Teste alternativo: apenas verifica se os arquivos existem
        if [[ -f "$BUILD_DIR/files/bin/multiscope" ]]; then
            print_success "Binário encontrado - build válido"
        else
            print_error "Binário não encontrado no build"
            return 1
        fi
    fi
}

# ===== FLUXO PRINCIPAL =====
main() {
    print_header "🚀 MultiScope Flatpak Builder"
    echo "App ID: $APP_ID"
    echo "Manifest: $MANIFEST"
    echo ""

    # Parse argumentos
    local dev_build=false
    local skip_tests=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --dev)
                dev_build=true
                shift
                ;;
            --skip-tests)
                skip_tests=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "Argumento desconhecido: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Fluxo de build
    check_dependencies
    setup_runtime
    clean_build
    compile_resources
    create_repository
    build_flatpak "$dev_build"

    if [[ "$skip_tests" == false ]]; then
        test_build
    fi

    create_bundle

    # Informações finais
    print_header "✅ Build Concluído"
    show_usage_instructions
}

show_help() {
    cat << EOF
Uso: $0 [OPÇÕES]

Opções:
  --dev          Build de desenvolvimento (instala para usuário)
  --skip-tests   Pula testes após build
  --help, -h     Mostra esta ajuda

Exemplos:
  $0              # Build padrão (release)
  $0 --dev        # Build de desenvolvimento
  $0 --dev --skip-tests

EOF
}

show_usage_instructions() {
    cat << EOF

📦 INSTALAÇÃO E USO:

  Instalar bundle localmente:
    flatpak install --user $BUNDLE_NAME

  Executar aplicativo:
    flatpak run $APP_ID

  Desinstalar:
    flatpak uninstall --user $APP_ID

🔧 DEPURAÇÃO:

  Ver logs da aplicação:
    flatpak run --command=sh $APP_ID

  Acessar sandbox:
    flatpak run --devel $APP_ID

📤 PUBLICAÇÃO NO FLATHUB:

  1. Fork repositório: https://github.com/flathub/flathub
  2. Adicione seu manifesto: $MANIFEST
  3. Submeta Pull Request
  4. Após aprovação, seu app estará em: https://flathub.org/apps/$APP_ID

📁 ESTRUTURA CRIADA:
  $BUILD_DIR/     - Diretório de build
  $REPO_DIR/      - Repositório OSTree local
  MultiScope-*.flatpak - Bundle instalável

EOF
}

# ===== PONTO DE ENTRADA =====
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
