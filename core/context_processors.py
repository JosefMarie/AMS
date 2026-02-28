from .models import SystemSetting

def global_settings(request):
    return {
        'site_settings': SystemSetting.get_settings()
    }

def unread_notifications(request):
    if request.user.is_authenticated:
        # Get unread notifications for the user
        notifications = request.user.notifications.filter(is_read=False).order_by('-created_at')
        return {
            'unread_notifications': notifications,
            'unread_notifications_count': notifications.count()
        }
    return {}
