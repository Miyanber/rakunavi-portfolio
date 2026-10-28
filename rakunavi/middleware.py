from colorama import init, Back, Fore, Style
init(autoreset=True) 

from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponseForbidden

import subprocess, difflib

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
        if ip:
            ip = ip.split(',')[0]
        
        cache_key = f"rate_limit_{ip}"
        requests_made = cache.get(cache_key, 0)

        if requests_made >= 2*60:  # 1分間にX回のリクエストを許可
            print("Too many requests !! \n")
            return HttpResponseForbidden('Too many requests, Access denied.\n')

        cache.set(cache_key, requests_made + 1, timeout=60)  # 60秒間の制限

        response = self.get_response(request)
        return response
