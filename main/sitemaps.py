from django.contrib import sitemaps
from django.contrib.sitemaps import Sitemap
from .models import *
from main.mixins import get_permission

def can_display_home():
    get_permission().display_introduction

class ExhibitionDetailsSitemap(Sitemap):
    changefreq = "daily"    # 更新頻度の目安（例：daily, weekly）
    priority = 0.5      # 相対的重要度（0.0〜1.0）

    def items(self):
        # 審査通過済みの展示のみ対象
        if can_display_home:
            return Exhibition.objects.all().order_by('id')
        else:
            return Exhibition.objects.none()
        

class PerformanceDetailsSitemap(Sitemap):
    changefreq = "daily"    # 更新頻度の目安（例：daily, weekly）
    priority = 0.5      # 相対的重要度（0.0〜1.0）

    def items(self):
        # 審査通過済みのみ対象
        if can_display_home:
            return Performance.objects.all().order_by('id')
        else:
            return Performance.objects.none()
    

class StaticViewSitemap(sitemaps.Sitemap):
    priority = 1.0
    changefreq = "daily"

    def items(self):
        return ["main:index", "main:slogans", "main:credits"]

    def location(self, item):
        return reverse(item)
