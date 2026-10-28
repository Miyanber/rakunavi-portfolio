from django.contrib import sitemaps
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import *
from main.mixins import get_permission

def can_display_home():
    get_permission().display_sports_fes

class Sports_FesViewSitemap(sitemaps.Sitemap):
    priority = 1.0
    changefreq = "daily"

    def items(self):
        if can_display_home:
            return ["sports_fes:index", "sports_fes:program_list", "sports_fes:team", "sports_fes:facilities", "sports_fes:access", ]
        else:
            return []

    def location(self, item):
        return reverse(item)
