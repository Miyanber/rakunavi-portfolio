from django import template
from django.urls import reverse
import datetime


register = template.Library()

@register.simple_tag
def percentage(value, all):
    return (value / all) * 100

@register.simple_tag
def percentage_datetime(event_start, begin_at, seconds):
    if type(event_start) == datetime.time:
        event_start = datetime.datetime.combine(begin_at, event_start)
    # if type(begin_at) == datetime.time:
    #     begin_at = datetime.datetime.combine(datetime.datetime.today(), begin_at)
    
    return ((event_start.timestamp() - begin_at.timestamp()) / seconds) * 100

@register.simple_tag
def jump_to_exhibitions_search(query):
    """
    JumpToExhibitionSearchView の URL を生成します。
    """
    search_url = f"{reverse('main:jump_to_exhibitions_search')}?query={query}"
    return search_url

@register.filter
def congestion_status(attraction):
    if attraction and attraction.wait_time:
        # ordered_attractions がある場合は wait_time を優先
        wt = attraction.wait_time
        if wt > 100:
            return "crowded"
        elif wt > 60:
            return "busy"
        elif wt > 30:
            return "normal"
        elif wt >= 0:
            return "empty"
            
        # それ以外は congestion_level を参照
        level = attraction.congestion_level
        #  未設定-1の場合は""になる
        if level == 0:
            return "empty"
        elif level == 1:
            return "normal"
        elif level == 2:
            return "busy"
        elif level == 3:
            return "crowded"
    return ""
