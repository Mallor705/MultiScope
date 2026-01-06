#!/bin/bash
# Automated release script for Twinverse

set -e  # Exit on error

# Utility functions
print_header() {
    echo -e "\n\033[1;34m=== $1 ===\033[0m"
}

print_success() {
    echo -e "\033[1;32m✓ $1\033[0m"
}

print_error() {
    echo -e "\033[1;31m✗ $1\033[0m" >&2
}

# Function to check dependencies
check_dependencies() {
    print_header "Checking Dependencies"

    local missing_deps=()

    for cmd in git python3; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps+=("$cmd")
        fi
    done

    # Check if we're in a git repository
    if [[ ! -d ".git" ]]; then
        print_error "Not in a git repository"
        missing_deps+=("git-repo")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi

    print_success "All dependencies verified"
}

# Function to get current version
get_current_version() {
    if [[ -f "version" ]]; then
        cat version
    else
        echo "0.9.0"  # Default version
    fi
}

# Function to check for uncommitted changes
check_git_status() {
    if [[ -n $(git status --porcelain) ]]; then
        print_error "There are uncommitted changes in the repository"
        echo "Please commit or revert changes before creating a release"
        exit 1
    fi
}

# Function to create release
create_release() {
    local version="$1"
    local release_type="$2"

    print_header "Creating Release $version ($release_type)"

    # Update version
    python scripts/version_manager.py "$version"

    # Commit version changes
    print_header "Committing changes"
    git add version share/metainfo/io.github.mall0r.Twinverse.metainfo.xml README.md docs/README.pt-br.md docs/README.es.md scripts/package-appimage.sh
    git commit -m "Bump version to $version"

    # Create tag
    print_header "Creating tag"
    git tag "v$version"

    print_success "Release $version created successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Push changes and tag:"
    echo "   git push origin main"
    echo "   git push origin v$version"
    echo ""
    echo "2. To create packages, run:"
    echo "   ./scripts/package-appimage.sh  # For AppImage"
    echo "   ./scripts/package-flatpak.sh   # For Flatpak"
    }

# Function to show help
show_help() {
    cat << EOF
Twinverse Release Script

Usage: $0 [OPTIONS] [VERSION]

Options:
  --major          Create a major release (x.0.0)
  --minor          Create a minor release (0.y.0)
  --patch          Create a patch release (0.0.z)
  --custom <ver>   Create a custom release
  --help, -h       Show this help

Examples:
  $0 --major              # Create major release: 1.2.3 -> 2.0.0
  $0 --minor              # Create minor release: 1.2.3 -> 1.3.0
  $0 --patch              # Create patch release: 1.2.3 -> 1.2.4
  $0 --custom 2.1.5       # Create custom release

EOF
}

# Function to increment version
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

# Parse arguments
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
                print_error "Option --custom requires a version"
                exit 1
            fi
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        -*)
            print_error "Unknown option: $1"
            show_help
            exit 1
            ;;
        *)
            new_version="$1"
            shift
            ;;
    esac
done

# Version format validation
if ! [[ $new_version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    print_error "Invalid version format: $new_version"
    print_error "Use format x.y.z (e.g., 1.0.0)"
    exit 1
fi

# Check dependencies
check_dependencies

# Check git status
check_git_status

# Confirmation
print_header "Release Information"
echo "Current version: $current_version"
echo "New version: $new_version"
echo "Type: $release_type"

read -p "Do you really want to create release $new_version? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "Operation cancelled."
    exit 0
fi

# Create the release
create_release "$new_version" "$release_type"
