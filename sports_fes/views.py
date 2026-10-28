from typing import Any

from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, ListView, DetailView, UpdateView
from django.shortcuts import render
from django.conf import settings

from .models import *

from rakunavi.utils import generate_qr_base64
from main. views import get_file_response

from main.mixins import get_permission



def _grade_color_map() -> dict:
    """GradeColor を {grade_num: color} の辞書で返す共通ヘルパー"""
    return {gc.grade_num: gc.color for gc in GradeColor.objects.all()}
from .forms import ProgramSearchForm, TeamInfoForm
from main.mixins import Sports_FesIntroductionLevelMixin, UseTokenMixin
from config.models import Credit, Sports_FesInfo

def _grade_meta():
    color_map = _grade_color_map()

    return [
        {
            "num": n,
            "color": color_map.get(n, "cccccc"),
        }
    for n in range(1, 8)
    ] #375で追加

class IndexView(Sports_FesIntroductionLevelMixin, TemplateView):
    template_name = "sports_fes/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context["assets"] = Sports_FesInfo.objects.annotate(
            high_year = F("year") - 1962,   #第N回を判断するためのマジックナンバー
            junior_year = F("year") - 1985,
        ).order_by("-year").first() #最新の年度のものを取得
        context["teams"] = Team.objects.filter(points__gt=0).order_by("-points")
        return context


class TeamView(Sports_FesIntroductionLevelMixin, TemplateView):
    template_name = "sports_fes/team.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teams_by_key = Team.objects.prefetch_related("classes").in_bulk(field_name="name")

        context["teams"] = [
            {
                "key": key,
                "label": label,
                "obj": team,
                # Classes DB不要。Team モデルのメソッドで動的生成
                "grade_blocks": team.get_grade_blocks() if team else [],
            }
            for key, label in Team.TEAM_CHOICES
            if (team := teams_by_key.get(key)) or True
        ]
        return context


class FacilitiesView(Sports_FesIntroductionLevelMixin, TemplateView):
    template_name = "sports_fes/facilities.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        field_guide = FieldGuide.objects.first()
        context["field_image_url"] = field_guide.image.url if field_guide else ""
        context["alt"] = Facility_Alt.objects.first()
        return context


class AccessView(Sports_FesIntroductionLevelMixin, TemplateView):
    template_name = "sports_fes/access.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["schedules"] = KintetsuSchedule.objects.order_by("Mukaijima_Departure_Time")
        context["explanation"] = KintetsuExplanation.objects.first()
        return context


class ProgramListView(Sports_FesIntroductionLevelMixin, ListView):
    model = Program
    template_name = "sports_fes/program.html"
    context_object_name = "programs"
 
    def get_queryset(self):
        queryset = Program.objects.all()
        form = ProgramSearchForm(self.request.GET or None)
 
        if form.is_valid():
            if query := form.cleaned_data.get("query"):
                queryset = queryset.filter(name__icontains=query) | queryset.filter(
                    description__icontains=query
                )
            # grades が JSONField になったため、含まれる学年番号でフィルタ
            if grade_nums := form.cleaned_data.get("grade_nums"):
                from django.db.models import Q
                q = Q(grades=[])  # 空リスト（全学年対象）は常にヒット
                for g in grade_nums:
                    # SQLite互換: JSON文字列に数値が含まれるか文字列検索
                    # 1桁固定（1〜6）なので誤ヒットなし
                    q |= Q(grades__icontains=g)
                queryset = queryset.filter(q).distinct()
 
        return queryset
 
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = ProgramSearchForm(self.request.GET or None)
        context["grade_color_map"] = _grade_color_map()

        context["grade_meta"] = _grade_meta() #375で追加
 
        programs = context["programs"]
        context["morning"] = programs.filter(session=Program.MORNING)
        context["afternoon"] = programs.filter(session=Program.AFTERNOON)
 
        return context


class ProgramDetailView(Sports_FesIntroductionLevelMixin, DetailView):
    model = Program
    template_name = "sports_fes/program_detail.html"
    context_object_name = "program"
    slug_field = "number"
    slug_url_kwarg = "number"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["grade_color_map"] = _grade_color_map()

        context["grade_meta"] = _grade_meta() #375で追加

        return context


class CreditsView(Sports_FesIntroductionLevelMixin, ListView):
    template_name = "main/credits.html"
    model = Credit

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        context["developers"] = qs.filter(is_developer=True)
        context["contributors"] = qs.filter(is_developer=False)
        return context


class ComingSoonView(TemplateView):
    template_name = "sports_fes/coming_soon.html"


class SlogansListView(Sports_FesIntroductionLevelMixin, ListView):
    # 過去含むスローガン一覧ビュー
    model = Sports_FesInfo
    paginate_by = 20
    template_name = "sports_fes/slogan.html"
    context_object_name = "slogans"

    def get_context_data(self, **kwargs) -> dict:
        context_data = super().get_context_data(**kwargs)
        # year=NULLを除外しないと、空objをhtmlで参照してしまいエラーになる
        context_data["slogans"] = Sports_FesInfo.objects.order_by("-year").exclude(year=None)
        context_data["assets"] = Sports_FesInfo.objects.annotate(
            high_year = F("year") - 1962,   #第N回を判断するためのマジックナンバー
            junior_year = F("year") - 1985,
        ).order_by("-year").first() #最新の年度のものを取得
        return context_data

class DeveloperportalView(TemplateView):
    template_name = "sports_fes/developer_portal.html"

    # 後でセキュリティ項目追加

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["debug"] = settings.DEBUG
        context["LANGUAGE_CODE"] = settings.LANGUAGE_CODE
        context["TIME_ZONE"] = settings.TIME_ZONE

        return context

def preview_403(request):
    return render(request, "sports_fes/error_pages/403.html", status=403)
def preview_404(request):
    return render(request, "sports_fes/error_pages/404.html", status=404)
def preview_500(request):
    return render(request, "sports_fes/error_pages/500.html", status=500)
def preview_400(request):
    return render(request, "sports_fes/error_pages/400.html", status=400)
def preview_csrf(request):
    return render(request, "sports_fes/error_pages/403_csrf.html", status=403)


class TeamInfoUpdateView(UseTokenMixin, UserPassesTestMixin, UpdateView):
    model = Team
    form_class = TeamInfoForm
    template_name = "sports_fes/team_info_form.html"

    # UseTokenMixinのdispatch関数でセッションにトークンは保存される

    def test_func(self):
        team= get_object_or_404(Team, pk=self.kwargs["pk"])
        token = self.request.session.get("edit_token")  # セッションから取得
        from main.views import safe_token_compare
        permission = get_permission()
        user_can_edit : bool = safe_token_compare(team.token, token) and permission.can_edit_team_info
        return self.request.user.is_superuser or user_can_edit
    
    def handle_no_permission(self):
        return redirect('main:under_review')

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        return context
    
    def get_success_url(self) -> str:
        self.request.session['success'] = True
        return reverse("sports_fes:team", query={"token" : str(self.object.token)})

# QRコード印刷
def download_team_qr_pdf(request):
    if not request.user.is_superuser:
        raise PermissionDenied()
    
    context = {
        "objects": [],
    }

    for team in Team.objects.order_by("pk"):
        url = request.build_absolute_uri(
            reverse("sports_fes:team_info_update", kwargs={"pk": team.pk})
            + f"?token={team.token}"
        )

        context["objects"].append({
            "name": team.get_name_display(),
            "qr": generate_qr_base64(url),
        })

    return get_file_response(
        "sports_fes/export/team_info_form_print.html",
        context,
        filename="体育祭応援団コンテンツ作成QRコード.pdf",
    )
