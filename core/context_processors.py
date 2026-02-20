from .models import SystemSetting

def global_settings(request):
    return {
        'site_settings': SystemSetting.get_settings()
    }
