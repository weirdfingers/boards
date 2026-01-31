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
import json
import subprocess
import sys
import time


def get_latest_run_id() -> str | None:
    """Get the databaseId of the latest version-bump.yml run."""
    try:
        result = subprocess.run(
            [
                "gh",
                "run",
                "list",
                "--workflow",
                "version-bump.yml",
                "--limit",
                "1",
                "--json",
                "databaseId",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        if data:
            return str(data[0]["databaseId"])
        return None
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def get_latest_release_version() -> str | None:
    """Get the tag name of the latest release."""
    try:
        result = subprocess.run(
            [
                "gh",
                "release",
                "list",
                "--limit",
                "1",
                "--json",
                "tagName",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        if data:
            tag = data[0]["tagName"]
            if tag.startswith("v"):
                return tag[1:]
            return tag
        return None
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None


def trigger_workflow(bump_type: str, wait: bool = False) -> None:
    """
    Trigger the GitHub Actions workflow.

    Args:
        bump_type: Type of version bump ("major", "minor", or "patch")
        wait: Whether to wait for the workflow to complete and print the new version

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

    # Get latest run ID before triggering if we need to wait
    old_run_id = None
    if wait:
        old_run_id = get_latest_run_id()

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

        if not wait:
            print("\nMonitor the workflow at:", file=sys.stderr)
            print("  gh run watch", file=sys.stderr)
            print("Or view in browser:", file=sys.stderr)
            print("  gh workflow view version-bump.yml --web", file=sys.stderr)
            return

        print("Waiting for workflow run to start...", file=sys.stderr)

        # Wait for new run
        start_time = time.time()
        new_run_id = None
        while time.time() - start_time < 60:
            current_id = get_latest_run_id()
            if current_id and current_id != old_run_id:
                new_run_id = current_id
                break
            time.sleep(2)

        if not new_run_id:
            print(
                "Error: Timed out waiting for workflow run to start.", file=sys.stderr
            )
            sys.exit(1)

        print(f"Workflow run started: {new_run_id}", file=sys.stderr)
        print("Waiting for completion...", file=sys.stderr)

        subprocess.run(["gh", "run", "watch", new_run_id], check=True)

        # Workflow finished successfully
        version = get_latest_release_version()
        if version:
            print(version)
        else:
            print("Warning: Could not determine new version.", file=sys.stderr)

    except subprocess.CalledProcessError as e:
        print(f"Error in workflow execution: {e}", file=sys.stderr)
        if hasattr(e, "stderr") and e.stderr:
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
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for workflow completion and print new version",
    )

    args = parser.parse_args()

    try:
        trigger_workflow(args.bump_type, wait=args.wait)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
