from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import include, path

urlpatterns = [path("admin/", admin.site.urls), path("api/", include("apps.core.urls"))]
if settings.DEBUG:
    # Local developers sometimes open the Django port directly after an old
    # runserver process is left behind. Make that mistake recoverable by
    # sending the browser to the real Vue entry instead of a blank 404 page.
    urlpatterns.insert(0, path("", lambda request: HttpResponseRedirect("http://127.0.0.1:5173/")))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
