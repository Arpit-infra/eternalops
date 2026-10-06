"""In-App Notifications API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.notifications import NotificationsResponse
from app.services.notification_service import NotificationService, get_notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationsResponse, summary="List notifications")
def get_notifications(
    unread_only: bool = Query(False, description="Filter only unread notifications"),
    limit: int = Query(50, ge=1, le=200),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationsResponse:
    """Retrieve notifications list."""
    return service.get_notifications(unread_only=unread_only, limit=limit)


@router.post("/{notification_id}/read", summary="Mark notification as read")
def mark_notification_read(
    notification_id: str,
    service: NotificationService = Depends(get_notification_service),
):
    """Mark a specific notification as read."""
    success = service.mark_as_read(notification_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Notification '{notification_id}' not found")
    return {"success": True, "id": notification_id}


@router.post("/read-all", summary="Mark all notifications as read")
def mark_all_notifications_read(
    service: NotificationService = Depends(get_notification_service),
):
    """Mark all notifications as read."""
    count = service.mark_all_as_read()
    return {"success": True, "marked_count": count}
