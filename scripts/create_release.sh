#!/bin/bash
# Script automatizado para criar releases do MultiScope

set -e  # Sai com erro se algum comando falhar

# Funções de utilitário
print_header() {
    echo -e "\n\033[1;34m=== $1 ===\033[0m"
}

print_success() {
    echo -e "\033[1;32m✓ $1\033[0m"
}

print_error() {
    echo -e "\033[1;31m✗ $1\033[0m" >&2
}

# Função para verificar dependências
check_dependencies() {
    print_header "Verificando Dependências"

    local missing_deps=()

    for cmd in git python3; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done

    # Verifica se estamos em um repositório git
    if [[ ! -d ".git" ]]; then
        print_error "Não está em um repositório git"
        missing_deps+=("git-repo")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Dependências ausentes: ${missing_deps[*]}"
        exit 1
    fi

    print_success "Todas dependências verificadas"
}

# Função para obter a versão atual
get_current_version() {
    if [[ -f "version" ]]; then
        cat version
    else
        echo "0.9.0"  # Versão padrão
    fi
}

# Função para verificar se há alterações não commitadas
check_git_status() {
    if [[ -n $(git status --porcelain) ]]; then
        print_error "Há alterações não commitadas no repositório"
        echo "Por favor, commit ou revert as alterações antes de criar uma release"
        exit 1
    fi
}

# Função para criar release
create_release() {
    local version="$1"
    local release_type="$2"

    print_header "Criando Release $version ($release_type)"

    # Atualiza a versão
    python scripts/version_manager.py "$version"

    # Commit das alterações de versionamento
    print_header "Fazendo commit das alterações"
    git add version share/metainfo/io.github.mallor.MultiScope.metainfo.xml README.md docs/README.pt-br.md docs/README.es.md scripts/package-appimage.sh
    git commit -m "Bump version to $version"

    # Cria tag
    print_header "Criando tag"
    git tag "v$version"

    print_success "Release $version criada com sucesso!"
    echo ""
    echo "Próximos passos:"
    echo "1. Faça push das alterações e da tag:"
    echo "   git push origin main"
    echo "   git push origin v$version"
    echo ""
    echo "2. Para criar pacotes, execute:"
    echo "   ./scripts/package-appimage.sh  # Para AppImage"
    echo "   ./scripts/package-flatpak.sh   # Para Flatpak"
    }

# Função para mostrar ajuda
show_help() {
    cat << EOF
Script de Release do MultiScope

Uso: $0 [OPÇÕES] [VERSÃO]

Opções:
  --major          Cria uma release major (x.0.0)
  --minor          Cria uma release minor (0.y.0)
  --patch          Cria uma release patch (0.0.z)
  --custom <ver>   Cria uma release com versão personalizada
  --help, -h       Mostra esta ajuda

Exemplos:
  $0 --major              # Cria release major: 1.2.3 -> 2.0.0
  $0 --minor              # Cria release minor: 1.2.3 -> 1.3.0
  $0 --patch              # Cria release patch: 1.2.3 -> 1.2.4
  $0 --custom 2.1.5       # Cria release com versão personalizada

EOF
}

# Função para incrementar versão
increment_version() {
    local version="$1"
    local part="$2"

    IFS='.' read -ra parts <<< "$version"
    local major="${parts[0]}"
    local minor="${parts[1]}"
    local patch="${parts[2]}"

    case "$part" in
        "major")
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        "minor")
            minor=$((minor + 1))
            patch=0
            ;;
        "patch")
            patch=$((patch + 1))
            ;;
    esac

    echo "${major}.${minor}.${patch}"
}

# Parse de argumentos
if [[ $# -eq 0 ]]; then
    show_help
    exit 1
fi

current_version=$(get_current_version)
new_version=""
release_type="custom"

while [[ $# -gt 0 ]]; do
    case $1 in
        --major)
            new_version=$(increment_version "$current_version" "major")
            release_type="major"
            shift
            ;;
        --minor)
            new_version=$(increment_version "$current_version" "minor")
            release_type="minor"
            shift
            ;;
        --patch)
            new_version=$(increment_version "$current_version" "patch")
            release_type="patch"
            shift
            ;;
        --custom)
            if [[ -n "$2" ]]; then
                new_version="$2"
                shift 2
            else
                print_error "Opção --custom requer uma versão"
                exit 1
            fi
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        -*)
            print_error "Opção desconhecida: $1"
            show_help
            exit 1
            ;;
        *)
            new_version="$1"
            shift
            ;;
    esac
done

# Validação de formato de versão
if ! [[ $new_version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    print_error "Formato de versão inválido: $new_version"
    print_error "Use o formato x.y.z (ex: 1.0.0)"
    exit 1
fi

# Verifica dependências
check_dependencies

# Verifica status do git
check_git_status

# Confirmação
print_header "Informações da Release"
echo "Versão atual: $current_version"
echo "Nova versão: $new_version"
echo "Tipo: $release_type"

read -p "Deseja realmente criar a release $new_version? (s/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Operação cancelada."
    exit 0
fi

# Cria a release
create_release "$new_version" "$release_type"
