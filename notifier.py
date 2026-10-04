"""ntfy push notification integration (ntfy.sh or self-hosted)."""

import requests
from config import NTFY_SERVER, NTFY_TOKEN, NTFY_TOPIC


def send_notification(title: str, message: str, priority: str = "default") -> bool:
    """Send a push notification via the configured ntfy server.

    Uses the JSON publish endpoint - HTTP headers are latin-1 only, which
    chokes on em dashes and emoji in the title; JSON fields are full UTF-8.

    Args:
        title: Notification title
        message: Notification body (ntfy Markdown)
        priority: min, low, default, high, urgent

    Returns:
        True if successful, False otherwise
    """
    headers = {"Authorization": f"Bearer {NTFY_TOKEN}"} if NTFY_TOKEN else {}
    try:
        response = requests.post(
            NTFY_SERVER,
            json={
                "topic": NTFY_TOPIC,
                "title": title,
                "message": message,
                "priority": {"min": 1, "low": 2, "default": 3, "high": 4, "urgent": 5}[priority],
                "tags": ["telescope"],
                "markdown": True,
            },
            headers=headers,
            timeout=30,
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Notification failed: {e}")
        return False


if __name__ == "__main__":
    # Test notification
    success = send_notification(
        title="ClearSkies Test",
        message="If you see this, notifications are working!",
        priority="default"
    )
    print("Sent!" if success else "Failed!")
