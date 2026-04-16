from typing import Iterable

from django.contrib.auth import get_user_model

from .models import Notification, NotificationType


User = get_user_model()


def create_notification(*, recipient, title: str, message: str, actor=None, notification_type=NotificationType.INFO, target_url: str = ''):
    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        title=title,
        message=message,
        notification_type=notification_type,
        target_url=target_url or None,
    )


def create_notifications_for_users(*, recipients: Iterable, title: str, message: str, actor=None, notification_type=NotificationType.INFO, target_url: str = ''):
    notifications = []
    for user in recipients:
        notifications.append(
            Notification(
                recipient=user,
                actor=actor,
                title=title,
                message=message,
                notification_type=notification_type,
                target_url=target_url or None,
            )
        )
    if notifications:
        Notification.objects.bulk_create(notifications)
    return notifications
