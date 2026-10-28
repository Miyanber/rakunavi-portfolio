from typing import Any
from django.forms.widgets import ClearableFileInput, TimeInput
from typing_extensions import deprecated

from config.models import FestivalDate

class PreviewableFileInput(ClearableFileInput):
    """写真のプレビュー表示用<br>Google Fonts読み込み必須"""    
    
    template_name = "main/widgets/previewable_file_input.html"
    preview_image = True
    
    class Media:
        js = ['main/js/widgets/previewable_file_input.js']
        css = {
            "all": ['main/css/widgets/previewable_file_input.css'],
        }

    def __init__(self, attrs=None, include_preview=True):
        super().__init__(attrs)
        if 'class' in self.attrs:
            self.attrs['class'] += ' preview-marker'
        else:
            self.attrs['class'] = 'preview-marker'
        self.include_preview = include_preview

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget'].update({
            'include_preview': self.include_preview,
        })
        return context


@deprecated("エラーを誘発するので現在は不使用")
class RakuNaviTimeInput(TimeInput):
    """らくなび用日付入力フォーム"""
    
    template_name = "main/widgets/time_input.html"
    
    def __init__(self, attrs=None):
        super().__init__(attrs)
        if 'class' in self.attrs:
            self.attrs['class'] += ' time-input'
        else:
            self.attrs['class'] = 'time-input'
    
    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)
        return context
    
    class Media:
        js = ['main/js/widgets/time_input.js']
        css = {
            "all": ['main/css/widgets/time_input.css'],
        }