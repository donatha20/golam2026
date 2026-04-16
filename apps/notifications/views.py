from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    notifications_qs = Notification.objects.filter(recipient=request.user).order_by('-created_at')

    paginator = Paginator(notifications_qs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'notifications': page_obj,
        'unread_count': notifications_qs.filter(is_read=False).count(),
    }
    return render(request, 'notifications/list.html', context)


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.mark_as_read()

    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    if notification.target_url:
        return redirect(notification.target_url)
    return redirect('notifications:list')


@login_required
@require_POST
def mark_all_notifications_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    next_url = request.POST.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('notifications:list')
