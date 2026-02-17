#!/usr/bin/env python3
"""
CLI entry point for Boards invite management.
"""

import os
import sys

import click
from dotenv import load_dotenv

from boards import __version__
from boards.logging import configure_logging, get_logger

logger = get_logger(__name__)


@click.group()
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(["debug", "info", "warning", "error"]),
    help="Log level (default: info)",
)
@click.version_option(version=__version__, prog_name="boards-invite")
def main(log_level: str) -> None:
    """Boards invite management — create invites and send via SMS."""
    load_dotenv()
    configure_logging(debug=(log_level == "debug"))


@main.command()
@click.argument("phone")
@click.option("--send", is_flag=True, help="Send activation link via Twilio SMS")
@click.option(
    "--url",
    default="http://localhost:3034",
    help="Base URL for the activation link (default: http://localhost:3034)",
)
def create(phone: str, send: bool, url: str) -> None:
    """Create an invite for PHONE (e.g. +15555555555) and optionally send via SMS."""
    from boards.tools.invite import create_invite, send_sms

    supabase_url = os.environ.get("BOARDS_SUPABASE_URL")
    service_role_key = os.environ.get("BOARDS_SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url or not service_role_key:
        logger.error("BOARDS_SUPABASE_URL and BOARDS_SUPABASE_SERVICE_ROLE_KEY must be set")
        sys.exit(1)

    from supabase import create_client

    supabase_client = create_client(supabase_url, service_role_key)

    code = create_invite(supabase_client, phone)
    if not code:
        sys.exit(1)

    link = f"{url}/activate?code={code}"
    click.echo(f"Link: {link}")

    if send:
        twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        twilio_token = os.environ.get("TWILIO_AUTH_TOKEN")
        twilio_from = os.environ.get("TWILIO_PHONE_NUMBER")

        if not twilio_sid or not twilio_token or not twilio_from:
            logger.error(
                "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER "
                "must be set to send SMS"
            )
            sys.exit(1)

        success = send_sms(phone, code, url, twilio_sid, twilio_token, twilio_from)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
