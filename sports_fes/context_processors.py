from django.utils import timezone

from .models import *
from config.models import Sports_FesInfo

import datetime

def common_context(request):
    """
    全てのテンプレートで共通して利用できるコンテキストを返します。
    """
    context = {}
        #   テンプレートの継承元変更のため、spots_fesがurlに含まれるなら変更する
    if  not "sports_fes/" in request.path:
        return context
    
    context["override_base"] = "sports_fes/base.html"
    context["general_images"] = GeneralImages.objects.first()
    context["datetime_now_year"] = datetime.datetime.now().year
    obj = Sports_FesInfo.objects.order_by("-year").first()
    if obj and obj.end_at < timezone.now():
        context["festival_ended"] = True
    return context
