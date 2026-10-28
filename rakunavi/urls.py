"""rakunavi URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import re_path
from django.urls import path, include
from django.views.static import serve

from django.conf.urls.static import static
from django.conf import settings

from baton.autodiscover import admin
from .admin.sites import RakuNaviAdminSite
admin.site.__class__ = RakuNaviAdminSite
from django.views.generic import TemplateView

from django.contrib.sitemaps.views import sitemap
from main.sitemaps import *
from sports_fes.sitemap import *

sitemaps = {
    'exhibitions': ExhibitionDetailsSitemap,
    'performances': PerformanceDetailsSitemap,
    'static': StaticViewSitemap,
    'sports_fes': Sports_FesViewSitemap,
}

handler403 = 'main.views.custom_403'
handler404 = 'main.views.custom_404'
handler500 = 'main.views.custom_500'
handler400 = 'main.views.custom_400'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('baton/', include('baton.urls')),
    path("", include("main.urls")),
    path("sports_fes/", include("sports_fes.urls")),
    path("ya/", include("ya.urls")),
    path('accounts/', include('main.account_urls')),
    path('', include('pwa.urls')),
    path('serviceworker.js', TemplateView.as_view(template_name="main/js/service_worker.js", content_type='application/javascript')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),

    re_path(
        r"^docs-images/(?P<path>.*)$",
        serve,
        {"document_root": "./docs/images"},  # ← imagesディレクトリ直下を配信
    ),
]

def set_static_urlpatterns():
    global urlpatterns
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

def set_media_urlpatterns():
    global urlpatterns
    urlpatterns += [re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT})]

if settings.CLOUD_SERVICE == 'aws':
    # 本番環境ではstaticファイル・mediaファイルともにS3,CloudFront経由で配信
    if settings.ENVIRONMENT == 'local':
        set_static_urlpatterns()
        set_media_urlpatterns()

if settings.CLOUD_SERVICE == 'vercel':
    # mediaファイルは本番・開発ともにSupabaseで配信
    set_static_urlpatterns()

if settings.DEBUG:
    urlpatterns += [
        path("__debug__/", include("debug_toolbar.urls")),
    ]


urlpatterns += [
    path("ckeditor5/", include('django_ckeditor_5.urls')),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
