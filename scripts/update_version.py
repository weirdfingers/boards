#!/usr/bin/env python3
"""
Version updating utility for release workflows.

This script safely updates version numbers from Git tags.
"""

import argparse
import re
import sys
from pathlib import Path


def validate_semver(version: str) -> bool:
    """Validate that a version string follows semantic versioning."""
    return bool(re.match(r'^\d+\.\d+\.\d+$', version))


def update_backend_version(version: str, base_dir: Path) -> None:
    """
    Update the backend version in __init__.py.

    Args:
        version: New version string
        base_dir: Base directory of the repository

    Raises:
        ValueError: If update fails
    """
    if not validate_semver(version):
        raise ValueError(f"Invalid version format: {version}")

    init_file = base_dir / "packages" / "backend" / "src" / "boards" / "__init__.py"
    if not init_file.exists():
        raise ValueError(f"File not found: {init_file}")

    try:
        content = init_file.read_text()
        updated = re.sub(
            r'__version__\s*=\s*"[^"]*"',
            f'__version__ = "{version}"',
            content
        )

        if updated == content:
            raise ValueError("Version update failed - no changes made")

        init_file.write_text(updated)
        print(f"Updated backend version to {version}", file=sys.stderr)

    except Exception as e:
        raise ValueError(f"Error updating version: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Update package version from tag")
    parser.add_argument("version", help="Version string to set")
    parser.add_argument("--package", choices=["backend", "frontend"], default="backend",
                        help="Package to update")
    parser.add_argument("--base-dir", type=Path, default=Path.cwd(),
                        help="Repository base directory")

    args = parser.parse_args()

    try:
        if args.package == "backend":
            update_backend_version(args.version, args.base_dir)
        else:
            # Frontend version updating is handled by pnpm
            print(f"Frontend version updating handled by pnpm", file=sys.stderr)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
