from django.contrib import admin
from .models import *
from django import forms
from django_ckeditor_5.fields import CKEditor5Widget
from django.core.exceptions import ValidationError


@admin.register(GradeColor)
class GradeColorAdmin(admin.ModelAdmin):
    list_display = ("grade_num", "color",)
    search_fields = ("color", )

# Programモデル用のフォームを定義
class ProgramAdminForm(forms.ModelForm):
    # descriptionフィールドにCKEditorウィジェットを適用
    description = forms.CharField(widget=CKEditor5Widget(), required=False)
    
    class Meta:
        model = Program
        fields = '__all__'

# Programモデルを新しいフォームで登録
@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    form = ProgramAdminForm
    list_display = ('session', 'number', 'name')
    list_filter = ('session',)
    search_fields = ('name',)


# Teamモデル用のフォーム
class TeamAdminForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditor5Widget())
    
    class Meta:
        model = Team
        fields = '__all__'

@admin.register(FieldGuide)
class FieldGuideAdmin(admin.ModelAdmin):
    list_display = ('image',)


@admin.register(KintetsuSchedule)
class KintetsuScheduleAdmin(admin.ModelAdmin):
    list_display = ('bound_for', )
    search_fields = ('bound_for', )

@admin.register(KintetsuExplanation)
class KintetsuExplanationAdmin(admin.ModelAdmin):
    list_display = ('content', 'show_schedule')
    search_fields = ('content', 'show_schedule')

    # 追加ボタン非表示
    def has_add_permission(self, request):
        return False
    # 削除ボタンも非表示
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Facility_Alt)
class Facility_Alt(admin.ModelAdmin):
    list_display = ("alt", )
    search_fields = ("alt", )

@admin.register(GeneralImages)
class GenrralImagesAdmin(admin.ModelAdmin):
    list_display = ("index_title", "fieldguide" )
    # 追加ボタン非表示
    def has_add_permission(self, request):
        return False
    # 削除ボタンも非表示
    def has_delete_permission(self, request, obj=None):
        return False

class TeamAdminForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = "__all__"

    def clean_classes(self):
        selected = self.cleaned_data.get("classes", SchoolClass.objects.none())
        team_pk = self.instance.pk  # 編集中の団（新規なら None）

        # 選択されたクラスが他の団にすでに配属されていないか確認
        conflicts = []
        for sc in selected:
            other_teams = sc.teams.exclude(pk=team_pk) if team_pk else sc.teams.all()
            if other_teams.exists():
                conflicts.append(f"{sc}（{other_teams.first()}）")

        if conflicts:
            raise forms.ValidationError(
                "以下のクラスはすでに別の団に配属されています：" + "、".join(conflicts)
            )

        return selected 


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    form = TeamAdminForm
    filter_horizontal = ["classes"]
    list_display = ["__str__", "points", "win", "points_updated_at"]

@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ["__str__", "grade_num", "class_num", "assigned_team"]
    list_filter = ["grade_num"]

    @admin.display(description="所属団")
    def assigned_team(self, obj):
        team = obj.teams.first()
        return team or "未配属"
