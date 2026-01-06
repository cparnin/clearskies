"""ntfy.sh push notification integration."""

import requests
from config import NTFY_TOPIC

NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"


def send_notification(title: str, message: str, priority: str = "default") -> bool:
    """Send a push notification via ntfy.sh.

    Args:
        title: Notification title
        message: Notification body
        priority: min, low, default, high, urgent

    Returns:
        True if successful, False otherwise
    """
    try:
        response = requests.post(
            NTFY_URL,
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": priority,
            },
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Notification failed: {e}")
        return False


if __name__ == "__main__":
    # Test notification
    success = send_notification(
        title="Clear Skies Test",
        message="If you see this, notifications are working!",
        priority="default"
    )
    print("Sent!" if success else "Failed!")
