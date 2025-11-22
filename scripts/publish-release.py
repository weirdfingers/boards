#!/usr/bin/env python3
"""
Trigger the GitHub Actions release workflow.

This script triggers the version-bump.yml workflow which will:
1. Bump all package versions
2. Commit and tag the new version
3. Create a GitHub release
4. Publish packages to PyPI and npm
"""

import argparse
import subprocess
import sys


def trigger_workflow(bump_type: str) -> None:
    """
    Trigger the GitHub Actions workflow.

    Args:
        bump_type: Type of version bump ("major", "minor", or "patch")

    Raises:
        subprocess.CalledProcessError: If gh command fails
    """
    print(f"Triggering release workflow with bump type: {bump_type}", file=sys.stderr)

    try:
        # Check if gh CLI is installed
        subprocess.run(
            ["gh", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("Error: GitHub CLI (gh) is not installed.", file=sys.stderr)
        print("Install it from: https://cli.github.com/", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("Error: Failed to run gh CLI.", file=sys.stderr)
        sys.exit(1)

    try:
        # Trigger the workflow
        subprocess.run(
            [
                "gh",
                "workflow",
                "run",
                "version-bump.yml",
                "-f",
                f"bump_type={bump_type}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        print("✓ Workflow triggered successfully!", file=sys.stderr)
        print("\nMonitor the workflow at:", file=sys.stderr)
        print("  gh run watch", file=sys.stderr)
        print("Or view in browser:", file=sys.stderr)
        print("  gh workflow view version-bump.yml --web", file=sys.stderr)

    except subprocess.CalledProcessError as e:
        print(f"Error triggering workflow: {e}", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Trigger GitHub Actions release workflow"
    )
    parser.add_argument(
        "bump_type",
        choices=["major", "minor", "patch"],
        help="Type of version bump",
    )

    args = parser.parse_args()

    try:
        trigger_workflow(args.bump_type)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
