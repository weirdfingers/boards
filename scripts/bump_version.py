#!/usr/bin/env python3
"""
Version bumping utility for Boards packages.

This script safely bumps version numbers following semantic versioning.
"""

import argparse
import re
import sys
from pathlib import Path


def validate_semver(version: str) -> bool:
    """Validate that a version string follows semantic versioning."""
    return bool(re.match(r'^\d+\.\d+\.\d+$', version))


def bump_version(current: str, bump_type: str) -> str:
    """
    Bump a semantic version number.

    Args:
        current: Current version string (e.g., "1.2.3")
        bump_type: Type of bump ("major", "minor", or "patch")

    Returns:
        New version string

    Raises:
        ValueError: If inputs are invalid
    """
    if not validate_semver(current):
        raise ValueError(f"Invalid version format: {current}")

    if bump_type not in ["major", "minor", "patch"]:
        raise ValueError(f"Invalid bump type: {bump_type}")

    parts = current.split(".")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    return f"{major}.{minor}.{patch}"


def get_current_version(package: str, base_dir: Path) -> str:
    """
    Get the current version of a package.

    Args:
        package: Package name ("backend" or "frontend")
        base_dir: Base directory of the repository

    Returns:
        Current version string

    Raises:
        ValueError: If version cannot be found
    """
    if package == "backend":
        init_file = base_dir / "packages" / "backend" / "src" / "boards" / "__init__.py"
        if not init_file.exists():
            raise ValueError(f"File not found: {init_file}")

        content = init_file.read_text()
        match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
        if not match:
            raise ValueError("Could not find __version__ in __init__.py")

        return match.group(1)

    elif package == "frontend":
        package_json = base_dir / "packages" / "frontend" / "package.json"
        if not package_json.exists():
            raise ValueError(f"File not found: {package_json}")

        import json
        data = json.loads(package_json.read_text())
        return data.get("version", "")

    else:
        raise ValueError(f"Unknown package: {package}")


def update_version(package: str, new_version: str, base_dir: Path) -> None:
    """
    Update the version in the package files.

    Args:
        package: Package name ("backend" or "frontend")
        new_version: New version string
        base_dir: Base directory of the repository

    Raises:
        ValueError: If update fails
    """
    if not validate_semver(new_version):
        raise ValueError(f"Invalid version format: {new_version}")

    if package == "backend":
        init_file = base_dir / "packages" / "backend" / "src" / "boards" / "__init__.py"
        if not init_file.exists():
            raise ValueError(f"File not found: {init_file}")

        content = init_file.read_text()
        updated = re.sub(
            r'__version__\s*=\s*"[^"]*"',
            f'__version__ = "{new_version}"',
            content
        )

        if updated == content:
            raise ValueError("Version update failed - no changes made")

        init_file.write_text(updated)

    elif package == "frontend":
        # For frontend, we'll let pnpm handle it
        # This is just for validation
        pass

    else:
        raise ValueError(f"Unknown package: {package}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Bump package version")
    parser.add_argument("package", choices=["backend", "frontend"],
                        help="Package to bump")
    parser.add_argument("bump_type", choices=["major", "minor", "patch"],
                        help="Type of version bump")
    parser.add_argument("--base-dir", type=Path, default=Path.cwd(),
                        help="Repository base directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")

    args = parser.parse_args()

    try:
        # Get current version
        current = get_current_version(args.package, args.base_dir)
        print(f"Current version: {current}", file=sys.stderr)

        # Calculate new version
        new_version = bump_version(current, args.bump_type)
        print(f"New version: {new_version}", file=sys.stderr)

        if not args.dry_run and args.package == "backend":
            # Update the version file
            update_version(args.package, new_version, args.base_dir)
            print(f"Updated {args.package} to {new_version}", file=sys.stderr)

        # Output the new version for GitHub Actions
        print(new_version)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()