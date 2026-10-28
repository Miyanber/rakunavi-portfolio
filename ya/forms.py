from django import forms
from django.contrib.auth import get_user_model
from django_ckeditor_5.widgets import CKEditor5Widget
from django.forms.widgets import CheckboxSelectMultiple

from ya.models import *

User = get_user_model() #importエラー回避のため

class DirectMessageForm(forms.ModelForm):
    class Meta:
        model = ChatMessages
        fields = ("content",)
        widgets = {
            "content": forms.Textarea(attrs={
                "id": "dm-content",
                "rows": 1,
                "placeholder": "メッセージを入力",
            })
        }
        
        def clean_content(self):
            content = self.cleaned_data["content"]
            if len(content) > 1000:
                raise forms.ValidationError("文字数が多すぎます。")
            return content

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("content", "image", )
        widgets = {
            "content" : CKEditor5Widget(
                attrs={"class": "django_ckeditor_5", },
                config_name="safer"   #settingsのsafer設定を使用
            ),
        }

class SearchUserForm(forms.Form):
    query = forms.CharField(
        label='検索',
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'ユーザー名・ユーザーIDから検索'}),
    )

class UserInfoForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("user_id", "username","self_introduction", )
        widgets = {
            "self_introduction" : CKEditor5Widget(
                attrs={"class": "django_ckeditor_5"},
                config_name="safer"   #settingsのsafer設定を使用
            ),
        }

class GroupSettingsForm(forms.ModelForm):
    class Meta:
        model = ChatGroups
        fields = ("name", "image", "description", "material_icon", "is_visible")
        # membersはJSとAJAXで制御するので含めない

class GroupCreateForm(forms.ModelForm):
    class Meta:
        model = ChatGroups
        fields = ("name", "image", "members", "description", "material_icon")
