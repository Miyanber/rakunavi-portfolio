from django import template
from django.forms.boundfield import BoundWidget
from sports_fes.models import Program

register = template.Library()

_GRADE_LABEL_MAP = dict(Program.GRADE_CHOICES)  # {1:"中1", 2:"中2", ...}


@register.filter
def get_item(dictionary, key):
    """{{ dict|get_item:key }} — int/str/BoundWidget どれでも引ける。
    key が BoundWidget の場合は自動的に選択肢の値(int)を取り出す。
    これにより {{ grade_color_map|get_item:checkbox }} と書ける。
    """
    if not isinstance(dictionary, dict):
        return None

    # BoundWidget が渡された場合は data["value"] を int として使う
    if isinstance(key, BoundWidget):
        try:
            key = int(key.data["value"])
        except (KeyError, TypeError, ValueError):
            return None

    value = dictionary.get(key)
    if value is None:
        try:
            value = dictionary.get(int(key))
        except (ValueError, TypeError):
            pass
    return value


@register.filter
def grade_label(grade_num):
    """{{ g|grade_label }} — 学年番号(int)を "中1" / "高1" 等の表示名に変換"""
    try:
        return _GRADE_LABEL_MAP.get(int(grade_num), str(grade_num))
    except (ValueError, TypeError):
        return str(grade_num)
