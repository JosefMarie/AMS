from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Seamless redirects for legacy scheme template URLs that conflicted with django admin
    path('admin/scheme-templates/', RedirectView.as_view(pattern_name='admin_scheme_templates', permanent=False)),
    path('admin/scheme-templates/<int:template_id>/delete/', RedirectView.as_view(pattern_name='delete_scheme_template', permanent=False)),
    
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
