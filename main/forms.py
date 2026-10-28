from typing import Any, Mapping
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm
from django.forms import modelformset_factory
from django.forms.widgets import HiddenInput, Textarea, TimeInput, RadioSelect

from .models import Performance, Song, Member, Exhibition, Attraction, FoodBooth, Event, ExhibitionReviewReport, PerformanceReviewReport, FoodBoothReviewReport, ExhibitionTag
from .widgets import PreviewableFileInput

from allauth.account.forms import LoginForm

from django_ckeditor_5.widgets import CKEditor5Widget

class RakuNaviModelForm(forms.ModelForm):
    'RakuNavi独自のフォームクラス。初期化時にクラスの追加とラベルのコロン削除を行う。'
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.label_suffix = ''
        for field in self.fields:
            self.init_field(field)
    
    def init_field(self, field_name) -> None:
        '全てのフィールドに対して行う初期化。'
        attrs = self.fields[field_name].widget.attrs
        existing_class = attrs.get('class', '')
        attrs['class'] = f"{existing_class} {field_name}".strip()


class OrderedModelForm(RakuNaviModelForm):
    '順番付きモデル用のモデルフォーム'
    
    template_name_div = 'main/forms/div.html'
    should_delete = forms.BooleanField(required=False, widget=HiddenInput)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.empty_permitted = False

    def init_field(self, field_name) -> None:
        super().init_field(field_name)
        field = self.fields[field_name]
        field.widget.attrs['placeholder'] = ' '
        if not field.required and hasattr(field, 'label'):
            if field.label:
                field.label += '（オプション）'
    
    class Meta:
        fields = ['order', 'should_delete']
        widgets = {
            'order': HiddenInput,
        }


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ''


class LoginForm(AuthenticationForm):
    pass


class ExhibitionForm(RakuNaviModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["explanation"].required = False
    
    def save(self, commit=True):
        try:
            return super().save(commit)
        except ValidationError as e:
            if "explanation" in e.message_dict:
                self.add_error("explanation", e.message_dict["explanation"])    #こちらにexplanationのエラーが来る
            else:
                self.add_error(None, e)  # フォーム全体のエラー
                return None

    class Meta:
        model = Exhibition
        fields = ['title', 'category', 'spots', 'overview', 'tags', 'explanation', 'thumbnail', 'background', 'video_file']
        widgets = {
            'explanation': CKEditor5Widget(
                attrs={"class": "django_ckeditor_5"},
                config_name="extends"   #settingsのextends設定を使用
            ),
            'thumbnail': PreviewableFileInput,
            'background': PreviewableFileInput,
        }


class AttractionForm(RakuNaviModelForm):
    def clean(self):
        cleaned_data = super().clean()
        time_required = cleaned_data.get("time_required")
        wait_time = cleaned_data.get("wait_time")
        if type(time_required) is int and time_required < 0:
            self.add_error("time_required", "所要時間は負にはできません。")
        if type(wait_time) is int and wait_time < 0:
            self.add_error("wait_time", "待ち時間は負にはできません。")
        return cleaned_data
    
    class Meta:
        model = Attraction
        fields = ['time_required', 'congestion_level', 'wait_time', 'announcement', 'ticket_status']
        widgets = {
            'congestion_level': RadioSelect(),
            'announcement': Textarea({"rows": "5"})
        }
    

class PerformanceForm(RakuNaviModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["message"].required = False
    
    def save(self, commit=True):
        try:
            return super().save(commit)
        except ValidationError as e:
            if "message" in e.message_dict:
                self.add_error("message", e.message_dict["message"])    #こちらにmessageのエラーが来る
            else:
                self.add_error(None, e)  # フォーム全体のエラー
                return None
            
    class Meta:
        model = Performance
        fields = ['name', 'genre', 'message', 'thumbnail', 'group_photo', 'date', 'begin_at', 'end_at', ]
        widgets = {
            'message': CKEditor5Widget(
                attrs={"class": "django_ckeditor_5"},
                config_name="extends"   #settingsのextends設定を使用
            ),
            'thumbnail': PreviewableFileInput,
            'group_photo': PreviewableFileInput,
            'begin_at': TimeInput(attrs={'type': 'time'}),
            'end_at': TimeInput(attrs={'type': 'time'}),
        }


ORDERING_FIELD_NAME = 'order'
DELETION_FIELD_NAME = 'should_delete'

class SongForm(OrderedModelForm):
    
    class Meta(OrderedModelForm.Meta):
        model = Song
        fields = OrderedModelForm.Meta.fields + ['title', 'artist', ]


SongFormSet = modelformset_factory(model=Song, form=SongForm, extra=0)
SongFormSet.template_name_div = 'main/forms/formsets/div.html'


class MemberForm(OrderedModelForm):
    class Meta(OrderedModelForm.Meta):
        model = Member
        fields = OrderedModelForm.Meta.fields + ['name', 'instrument', 'message']
        widgets = OrderedModelForm.Meta.widgets | {
            'thumbnail': PreviewableFileInput,
        }
        

MemberFormSet = modelformset_factory(model=Member, form=MemberForm, extra=0)
MemberFormSet.template_name_div = 'main/forms/formsets/div.html'


class EventForm(OrderedModelForm):
    def init_field(self, field_name):
        super().init_field(field_name)
        field = self.fields[field_name]
        field.widget.attrs['placeholder'] = field.label
    
    class Meta(OrderedModelForm.Meta):
        model = Event
        fields = OrderedModelForm.Meta.fields + ['name', 'spot', 'explanation', 'order', ]
        widgets = OrderedModelForm.Meta.widgets | {
            'explanation': Textarea({"rows": "3"}),
            'order': HiddenInput(),
        }


EventFormSet = modelformset_factory(model=Event, form=EventForm, extra=0)
EventFormSet.template_name_div = 'main/forms/formsets/div.html'


class FoodBoothForm(RakuNaviModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["message"].required = False
    
    def save(self, commit=True):
        try:
            return super().save(commit)
        except ValidationError as e:
            if "message" in e.message_dict:
                self.add_error("message", e.message_dict["message"])    #こちらにmessageのエラーが来る
            else:
                self.add_error(None, e)  # フォーム全体のエラー
                return None
            
    class Meta:
        model = FoodBooth
        fields = ('name', 'price', 'thumbnail', 'background', 'message')
        widgets = {
            'message': CKEditor5Widget(
                attrs={"class": "django_ckeditor_5"},
                config_name="extends"   #settingsのextends設定を使用
            ),
            'thumbnail': PreviewableFileInput,
            'background': PreviewableFileInput,
        }

# 検索フォーム
class ExhibitionSearchForm(forms.Form):
    query = forms.CharField(
        label='検索',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'タイトル、概要などから検索'}),
    )
    tags = forms.ModelMultipleChoiceField(
        label='タグ',
        queryset=ExhibitionTag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )


class ExhibitionReviewForm(forms.ModelForm):
    class Meta:
        model = ExhibitionReviewReport
        fields = ['status', 'exhibition', 'reason', 'in_charge_of']
        widgets = {
            'status': RadioSelect(),
            'reason': Textarea(attrs={'rows': 3}),
            'exhibition': HiddenInput(),
        }


class PerformanceReviewForm(forms.ModelForm):
    class Meta:
        model = PerformanceReviewReport
        fields = ['status', 'performance', 'reason', 'in_charge_of']
        widgets = {
            'status': RadioSelect(),
            'reason': Textarea(attrs={'rows': 3}),
            'performance': HiddenInput(),
        }


class FoodBoothReviewForm(forms.ModelForm):
    class Meta:
        model = FoodBoothReviewReport
        fields = ['status', 'food_booth', 'reason', 'in_charge_of']
        widgets = {
            'status': RadioSelect(),
            'reason': Textarea(attrs={'rows': 3}),
            'food_booth': HiddenInput(),
        }


class MapKeyForm(forms.Form):
    key = forms.CharField(
        label='マップの合言葉',
        max_length=30,
        widget=forms.TextInput(attrs={'placeholder': 'マップの合言葉を入力'}),
    )
