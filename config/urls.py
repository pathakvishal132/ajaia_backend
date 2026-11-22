"""URL configuration for the project."""

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404, JsonResponse
from django.urls import include, path, re_path


def health(_request):
    return JsonResponse({'status': 'ok'})


def spa_index(_request, *args, **kwargs):
    """Serve the Angular index.html for client-side routes (single-container deploy)."""
    index = settings.FRONTEND_DIST / 'index.html'
    if not index.is_file():
        raise Http404('Frontend build not found.')
    return FileResponse(open(index, 'rb'), content_type='text/html')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health, name='health'),
    path('api/auth/', include('accounts.urls')),
    path('api/documents/', include('documents.urls')),
    # Anything that is not the API, admin or a static asset is an Angular route.
    re_path(r'^(?!api/|admin/|static/).*$', spa_index, name='spa'),
]
