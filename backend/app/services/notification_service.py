"""In-app notification service."""

import logging
from datetime import datetime
from typing import List, Optional
import uuid

from app.schemas.notifications import NotificationItem, NotificationsResponse

logger = logging.getLogger("eternalops.notifications")


class NotificationService:
    """In-memory notification queue and manager."""

    def __init__(self, max_entries: int = 200):
        self._notifications: List[NotificationItem] = []
        self._max_entries = max_entries

    def notify(
        self,
        title: str,
        message: str,
        type_: str = "info",
        incident_id: Optional[str] = None,
        organization_id: str = "org_default",
        environment_id: str = "env_local_dev",
    ) -> NotificationItem:
        """Create a new notification."""
        now = datetime.utcnow()
        time_str = now.strftime("%H:%M:%S")
        nid = f"notif-{uuid.uuid4().hex[:8]}"

        item = NotificationItem(
            id=nid,
            title=title,
            message=message,
            type=type_,
            timestamp=now,
            time_str=time_str,
            read=False,
            incident_id=incident_id,
            organization_id=organization_id,
            environment_id=environment_id,
        )

        self._notifications.insert(0, item)
        if len(self._notifications) > self._max_entries:
            self._notifications.pop()

        logger.info("[Notification] [%s] %s: %s", type_.upper(), title, message)
        return item

    def get_notifications(self, unread_only: bool = False, limit: int = 50) -> NotificationsResponse:
        """Fetch notifications."""
        items = self._notifications
        if unread_only:
            items = [n for n in items if not n.read]

        unread_count = sum(1 for n in self._notifications if not n.read)
        return NotificationsResponse(
            total=len(self._notifications),
            unread_count=unread_count,
            notifications=items[:limit],
        )

    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        for n in self._notifications:
            if n.id == notification_id:
                n.read = True
                return True
        return False

    def mark_all_as_read(self) -> int:
        """Mark all notifications as read."""
        count = 0
        for n in self._notifications:
            if not n.read:
                n.read = True
                count += 1
        return count

    def clear(self) -> None:
        """Clear notifications (for tests)."""
        self._notifications.clear()


_notification_service_instance: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Dependency provider for singleton NotificationService."""
    global _notification_service_instance
    if _notification_service_instance is None:
        _notification_service_instance = NotificationService()
    return _notification_service_instance
