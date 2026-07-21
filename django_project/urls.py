from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from app.views import robots_txt

from django.contrib.sitemaps.views import sitemap
from app.sitemaps import StaticViewSitemap

sitemaps = {"static": StaticViewSitemap}

urlpatterns = [
    path("robots.txt", robots_txt),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path('admin/', admin.site.urls),
    path('account/', include('accounts.urls', namespace='accounts')),
    path('', include('app.urls')),
]

# Media servito direttamente dall'app (va bene per un progetto di piccole
# dimensioni; per traffico alto conviene un bucket S3/Cloudflare R2 + CDN).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
