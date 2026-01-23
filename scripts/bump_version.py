#!/usr/bin/env python3
"""
Version bumping utility for Boards packages.

This script safely bumps version numbers following semantic versioning.
"""

import argparse
import json
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


def get_backend_version(base_dir: Path) -> str:
    """
    Get the current version of the backend package.

    Args:
        base_dir: Base directory of the repository

    Returns:
        Current version string

    Raises:
        ValueError: If version cannot be found
    """
    init_file = base_dir / "packages" / "backend" / "src" / "boards" / "__init__.py"
    if not init_file.exists():
        raise ValueError(f"File not found: {init_file}")

    content = init_file.read_text()
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if not match:
        raise ValueError("Could not find __version__ in __init__.py")

    return match.group(1)


def get_frontend_version(base_dir: Path) -> str:
    """
    Get the current version of the frontend package.

    Args:
        base_dir: Base directory of the repository

    Returns:
        Current version string

    Raises:
        ValueError: If version cannot be found
    """
    package_json = base_dir / "packages" / "frontend" / "package.json"
    if not package_json.exists():
        raise ValueError(f"File not found: {package_json}")

    data = json.loads(package_json.read_text())
    version = data.get("version", "")
    if not version:
        raise ValueError("Could not find version in package.json")
    return version


def get_current_versions(base_dir: Path) -> tuple[str, str]:
    """
    Get current versions of both backend and frontend packages.

    Args:
        base_dir: Base directory of the repository

    Returns:
        Tuple of (backend_version, frontend_version)

    Raises:
        ValueError: If versions cannot be found or don't match
    """
    backend_version = get_backend_version(base_dir)
    frontend_version = get_frontend_version(base_dir)

    if backend_version != frontend_version:
        raise ValueError(
            f"Version mismatch: backend={backend_version}, frontend={frontend_version}"
        )

    return backend_version, frontend_version


def update_backend_version(new_version: str, base_dir: Path) -> None:
    """
    Update the version in the backend package.

    Args:
        new_version: New version string
        base_dir: Base directory of the repository

    Raises:
        ValueError: If update fails
    """
    if not validate_semver(new_version):
        raise ValueError(f"Invalid version format: {new_version}")

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
        raise ValueError("Backend version update failed - no changes made")

    init_file.write_text(updated)


def update_package_json_version(package_path: Path, new_version: str) -> None:
    """
    Update the version in a package.json file.

    Args:
        package_path: Path to the package directory
        new_version: New version string

    Raises:
        ValueError: If update fails
    """
    if not validate_semver(new_version):
        raise ValueError(f"Invalid version format: {new_version}")

    package_json = package_path / "package.json"
    if not package_json.exists():
        raise ValueError(f"File not found: {package_json}")

    data = json.loads(package_json.read_text())
    old_version = data.get("version", "")
    data["version"] = new_version

    if old_version == new_version:
        raise ValueError(f"Version update failed for {package_path.name} - no changes made")

    package_json.write_text(json.dumps(data, indent=2) + "\n")


def update_all_versions(new_version: str, base_dir: Path) -> None:
    """
    Update versions in all packages.

    Args:
        new_version: New version string
        base_dir: Base directory of the repository

    Raises:
        ValueError: If update fails
    """
    update_backend_version(new_version, base_dir)
    update_package_json_version(base_dir / "packages" / "frontend", new_version)
    update_package_json_version(base_dir / "packages" / "cli-launcher", new_version)
    # Auth packages
    update_package_json_version(base_dir / "packages" / "auth-supabase", new_version)
    update_package_json_version(base_dir / "packages" / "auth-clerk", new_version)
    update_package_json_version(base_dir / "packages" / "auth-jwt", new_version)


def prompt_bump_type() -> str:
    """
    Prompt the user for the bump type interactively.

    Returns:
        The selected bump type
    """
    print("Select version bump type:", file=sys.stderr)
    print("  1. patch (0.0.x)", file=sys.stderr)
    print("  2. minor (0.x.0)", file=sys.stderr)
    print("  3. major (x.0.0)", file=sys.stderr)

    while True:
        choice = input("Enter choice [1-3]: ").strip()
        if choice == "1":
            return "patch"
        elif choice == "2":
            return "minor"
        elif choice == "3":
            return "major"
        else:
            print("Invalid choice. Please enter 1, 2, or 3.", file=sys.stderr)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Bump package versions for all packages (backend, frontend, cli-launcher)"
    )
    parser.add_argument(
        "bump_type",
        nargs="?",
        choices=["major", "minor", "patch"],
        help="Type of version bump (if not provided, will prompt interactively)",
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path.cwd(),
        help="Repository base directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args()

    try:
        # Get bump type (prompt if not provided)
        bump_type = args.bump_type
        if bump_type is None:
            bump_type = prompt_bump_type()

        # Get current version (all packages should have the same version)
        current_version, _ = get_current_versions(args.base_dir)
        print(f"Current version: {current_version}", file=sys.stderr)

        # Calculate new version
        new_version = bump_version(current_version, bump_type)
        print(f"New version: {new_version}", file=sys.stderr)

        if not args.dry_run:
            # Update all package versions
            update_all_versions(new_version, args.base_dir)
            print(f"Updated all packages to {new_version}", file=sys.stderr)

        # Output the new version for GitHub Actions
        print(new_version)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
