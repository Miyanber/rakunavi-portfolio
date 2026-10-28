from django import forms
from .models import Program, Team
from main.widgets import PreviewableFileInput

class ProgramSearchForm(forms.Form):
    query = forms.CharField(
        label="検索",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            "placeholder": "プログラム名から検索",
            "class": "query-input",
        }),
    )
    grade_nums = forms.MultipleChoiceField(
        label="学年",
        choices=Program.GRADE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "tag-checkbox"}),
    )

    def clean_grade_nums(self):
        # フォームの値は文字列で来るので int に変換して返す
        return [int(g) for g in self.cleaned_data.get("grade_nums", [])]


class TeamInfoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].required = True
        # self.fields["main_image"].required = True
        self.fields["bg_image"].required = True

    class Meta:
        model = Team
        fields= ["description", "main_image", "bg_image"]
        widgets = {
            "main_image" : PreviewableFileInput,
            "bg_image" : PreviewableFileInput,
        }
