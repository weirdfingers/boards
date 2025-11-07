#!/usr/bin/env python3
"""
Version bumping utility for Boards packages.

This script safely bumps version numbers following semantic versioning.
All packages (backend, frontend, cli-launcher) are versioned together.
"""

import argparse
import json
import re
import subprocess
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


def get_current_version(base_dir: Path) -> str:
    """
    Get the current version from the backend package.

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
        raise ValueError("Version update failed - no changes made")

    init_file.write_text(updated)


def get_latest_tag() -> str | None:
    """
    Get the latest git tag.

    Returns:
        Latest tag name or None if no tags exist
    """
    try:
        result = subprocess.run(
            ["git", "tag", "-l", "v*", "--sort=-v:refname"],
            capture_output=True,
            text=True,
            check=True
        )
        tags = result.stdout.strip().split("\n")
        return tags[0] if tags and tags[0] else None
    except subprocess.CalledProcessError:
        return None


def generate_release_notes(new_version: str) -> dict[str, str]:
    """
    Generate release notes using GitHub CLI.

    Args:
        new_version: New version string

    Returns:
        Dictionary with 'title' and 'body' keys
    """
    try:
        # Check if gh CLI is available
        subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Warning: GitHub CLI not available, skipping release notes generation", file=sys.stderr)
        return {
            "title": f"v{new_version}",
            "body": f"Release version {new_version}"
        }

    # Get the previous tag
    previous_tag = get_latest_tag()

    if not previous_tag:
        print("Warning: No previous tag found, generating basic notes", file=sys.stderr)
        return {
            "title": f"v{new_version}",
            "body": f"Initial release version {new_version}"
        }

    # Generate release notes using GitHub CLI
    tag_name = f"v{new_version}"

    try:
        result = subprocess.run(
            [
                "gh", "api",
                "/repos/:owner/:repo/releases/generate-notes",
                "-f", f"tag_name={tag_name}",
                "-f", f"previous_tag_name={previous_tag}"
            ],
            capture_output=True,
            text=True,
            check=True
        )

        notes = json.loads(result.stdout)
        return {
            "title": notes.get("name", f"v{new_version}"),
            "body": notes.get("body", f"Release version {new_version}")
        }
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to generate release notes via GitHub API: {e.stderr}", file=sys.stderr)
        return {
            "title": f"v{new_version}",
            "body": f"Release version {new_version}"
        }
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse GitHub API response: {e}", file=sys.stderr)
        return {
            "title": f"v{new_version}",
            "body": f"Release version {new_version}"
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Bump version for all Boards packages (backend, frontend, cli-launcher)"
    )
    parser.add_argument("bump_type", choices=["major", "minor", "patch"],
                        help="Type of version bump")
    parser.add_argument("--base-dir", type=Path, default=Path.cwd(),
                        help="Repository base directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without making changes")
    parser.add_argument("--generate-notes", action="store_true",
                        help="Generate release notes based on commits and PRs")
    parser.add_argument("--notes-format", choices=["json", "markdown", "text"],
                        default="text",
                        help="Output format for release notes (default: text)")

    args = parser.parse_args()

    try:
        # Get current version from backend
        current = get_current_version(args.base_dir)
        print(f"Current version: {current}", file=sys.stderr)

        # Calculate new version
        new_version = bump_version(current, args.bump_type)
        print(f"New version: {new_version}", file=sys.stderr)

        if not args.dry_run:
            # Update the backend version file
            update_backend_version(new_version, args.base_dir)
            print(f"Updated backend to {new_version}", file=sys.stderr)
            print("Note: Frontend and CLI launcher versions will be updated by workflow", file=sys.stderr)

        # Generate release notes if requested
        if args.generate_notes:
            print("\nGenerating release notes...", file=sys.stderr)
            notes = generate_release_notes(new_version)

            if args.notes_format == "json":
                print(json.dumps(notes, indent=2))
            elif args.notes_format == "markdown":
                print(f"# {notes['title']}\n\n{notes['body']}")
            else:  # text
                print(f"\nTitle: {notes['title']}")
                print(f"\nBody:\n{notes['body']}")
        else:
            # Output the new version for GitHub Actions
            print(new_version)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
