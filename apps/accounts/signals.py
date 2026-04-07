from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone

from .models import UserSession


def _get_client_ip(request):
    if not request:
        return '0.0.0.0'

    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()

    return request.META.get('REMOTE_ADDR', '0.0.0.0')


@receiver(user_logged_in)
def create_user_session(sender, request, user, **kwargs):
    if not request:
        return

    if not request.session.session_key:
        request.session.save()

    session_key = request.session.session_key
    if not session_key:
        return

    UserSession.objects.update_or_create(
        session_key=session_key,
        defaults={
            'user': user,
            'ip_address': _get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'logout_time': None,
            'is_active': True,
        },
    )


@receiver(user_logged_out)
def close_user_session(sender, request, user, **kwargs):
    if not request:
        return

    session_key = request.session.session_key
    if not session_key:
        return

    UserSession.objects.filter(
        session_key=session_key,
        is_active=True,
    ).update(
        is_active=False,
        logout_time=timezone.now(),
    )
