"""Notification stubs — unrelated to the order pipeline.

This module exists to give the graph a component with no incoming call edges
from the order service, demonstrating isolation and community separation.
It intentionally defines a `get_status` function (also in orders.summary)
to create a duplicate symbol name across modules.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class Notification:
    recipient: str
    subject: str
    body: str
    channel: str  # email | sms | push


def get_status(notification_id: str) -> str:
    """Return delivery status for a notification (stub: always 'delivered')."""
    # NOTE: same name as orders.summary.get_status — intentional duplicate symbol
    return "delivered"


def send_email(recipient: str, subject: str, body: str) -> Notification:
    """Build and 'send' an email notification (stub — no real transport)."""
    return Notification(recipient=recipient, subject=subject, body=body, channel="email")


def send_sms(recipient: str, body: str) -> Notification:
    """Build and 'send' an SMS notification (stub)."""
    return Notification(recipient=recipient, subject="", body=body, channel="sms")


def dispatch(notification: Notification) -> bool:
    """Dispatch a pre-built notification via the appropriate channel."""
    if notification.channel not in ("email", "sms", "push"):
        return False
    # ponytail: stub dispatch; connect to real transport when needed
    return True
