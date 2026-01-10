#!/usr/bin/env python3
"""
Script to manage Twinverse versioning.

This script automatically updates the version in all necessary files
when a new version is defined.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path


def update_version_in_file(file_path, old_version, new_version):
    """Updates the version in a specific file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Specific replacements for different version formats
    updated_content = content

    # Update version in "x.y.z" format
    updated_content = re.sub(
        rf'(["\']){re.escape(old_version)}(["\'])',
        rf"\g<1>{new_version}\g<2>",
        updated_content,
    )

    # Update version in date format in metainfo.xml
    if "metainfo.xml" in str(file_path):
        current_date = datetime.now().strftime("%Y-%m-%d")
        # Update release date in metainfo.xml - considerando também o atributo type
        updated_content = re.sub(
            r'<release version="[^"]+" date="[^"]+"([^>]*>)',
            f'<release version="{new_version}" date="{current_date}"\\1',
            updated_content,
        )

    # Update version badge in README
    if "README" in str(file_path):
        updated_content = re.sub(r"Version-[0-9]+\.[0-9]+\.[0-9]+", f"Version-{new_version}", updated_content)

    if content != updated_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        print(f"✓ Updated: {file_path}")
        return True

    return False


def get_current_version():
    """Gets the current version from the version file."""
    version_file = Path("version")
    if version_file.exists():
        with open(version_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


def set_new_version(new_version, force=False):
    """Sets a new version and updates all relevant files."""
    old_version = get_current_version()

    if not old_version:
        print("Error: version file not found or empty")
        return False

    if old_version == new_version and not force:
        print(f"Version is already {new_version}")
        return True

    # Update the version file
    with open("version", "w", encoding="utf-8") as f:
        f.write(new_version)

    print(f"Updating version from {old_version} to {new_version}")

    # List of files that contain the version
    files_to_update = [
        "scripts/package-appimage.sh",
        "share/metainfo/io.github.mall0r.Twinverse.metainfo.xml",
        "README.md",
        "docs/README.pt-br.md",
        "docs/README.es.md",
        "io.github.mall0r.Twinverse.yaml",  # Although it doesn't contain version directly, it may contain references
        "scripts/package-flatpak.sh",
    ]

    updated_files = []

    for file_path in files_to_update:
        file_obj = Path(file_path)
        if file_obj.exists():
            if update_version_in_file(file_obj, old_version, new_version):
                updated_files.append(file_path)

    print(f"\n✓ Version updated successfully from {old_version} to {new_version}")
    print(f"Files updated: {len(updated_files)}")
    for file in updated_files:
        print(f"  - {file}")

    return True


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        current_version = get_current_version()
        if current_version:
            print(f"Usage: python {sys.argv[0]} <new_version> [force]")
            print(f"Current version: {current_version}")
        else:
            print(f"Usage: python {sys.argv[0]} <new_version> [force]")
            print("No current version found")
        return 1

    new_version = sys.argv[1]
    force = len(sys.argv) == 3 and sys.argv[2] == "force"

    # Validate version format (x.y.z)
    version_pattern = r"^[0-9]+\.[0-9]+\.[0-9]+$"
    if not re.match(version_pattern, new_version):
        print(f"Error: Invalid version format. Use x.y.z format (e.g., 0.11.2)")
        return 1

    if not set_new_version(new_version, force):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
