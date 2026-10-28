import datetime, os, requests
from django.core.cache import caches
cache = caches['default']
from django.db import transaction
from django.http import HttpResponseForbidden, HttpResponsePermanentRedirect
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone

from main.models import Exhibition, Performance, FoodBooth
from config.models import Slogan, Permission, NewDomainRedirectURL
from rakunavi import settings
from main.mixins import get_permission

from main.admin import *


class ProjectLastUpdatedMiddleware(MiddlewareMixin):
    """
    プロジェクト内のファイルの最終更新時刻を取得して、いつの変更か知る
    """

    def process_request(self, request):
        project_path = settings.BASE_DIR
        latest_update = 0

        for root, _, files in os.walk(project_path):
            for file in files:
                if file.endswith('.py') or file.endswith('.html') or file.endswith('.css') or file.endswith('.js'):    #ここのファイルが検索対象
                    file_path = os.path.join(root, file)
                    try:
                        last_modified = os.path.getmtime(file_path)
                        if last_modified > latest_update:
                            latest_update = last_modified
                    except FileNotFoundError:
                        print('ターゲットファイルなし')
                        continue

        # `request` に値を追加
        request.project_last_updated = datetime.datetime.fromtimestamp(latest_update) if latest_update > 0 else None    #ここでUnix時間から変換


class NewDomainRedirectMiddleware:
    CACHE_KEY = "new_domain_redirect"
    CACHE_TIMEOUT = 60 * 60 * 24 # 1日

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        redirect_config = self._get_redirect_config()

        if redirect_config and redirect_config["active"]:
            new_url = redirect_config["url"].rstrip("/")
            path = request.get_full_path()
            return HttpResponsePermanentRedirect(f"{new_url}{path}")    #永久リダイレクト

        return self.get_response(request)

    def _get_redirect_config(self):
        """キャッシュ優先でDBから設定を取得"""
        cached = cache.get(self.CACHE_KEY)
        if cached is not None:
            return cached

        try:
            obj = NewDomainRedirectURL.objects.get(pk=1)
            config = {"url": obj.url, "active": obj.active}
        except NewDomainRedirectURL.DoesNotExist:
            config = None

        cache.set(self.CACHE_KEY, config, self.CACHE_TIMEOUT)
        return config
