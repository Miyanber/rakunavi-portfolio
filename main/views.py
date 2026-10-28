from django.apps import apps
from django.core.files.storage import Storage
from django.conf import settings
from django.db.models import Q, Exists, OuterRef, Prefetch, Subquery, Max, Case, When, BooleanField
from django.db.models.base import Model as Model
from django.db.models.query import QuerySet
from django.http import Http404,HttpRequest, HttpResponse, HttpResponseForbidden, HttpResponseRedirect, JsonResponse, StreamingHttpResponse, FileResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, UpdateView, DetailView, ListView, CreateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from allauth.account.views import LoginView
from django.template.loader import render_to_string

from config.models import Credit, FestivalDate, Slogan, Permission, DefaultCounts
from main.models import *
from main.forms import PerformanceForm, SongFormSet, MemberFormSet, ExhibitionForm, AttractionForm, FoodBoothForm, EventFormSet, ExhibitionSearchForm, ExhibitionReviewForm, PerformanceReviewForm, FoodBoothReviewForm, MapKeyForm
from main.mixins import *

from io import BytesIO
from typing import Any
import unicodedata, markdown, mojimoji
from pathlib import Path
from urllib.parse import unquote, urlparse, urlunparse
import datetime, os, hmac, qrcode, random, sys, re


def safe_token_compare(a, b) -> bool:
    """ 
    タイミング攻撃を考慮した、トークンの比較のための関数。 
    """
    if a is None or b is None:  #hmac.compare_digestはnoneを含むとエラーを返すため
        return False
    else:
        return hmac.compare_digest(a, b)

class CustomLoginView(LoginView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        username = self.request.GET.get('username')
        password = self.request.GET.get('password')
        if username and password:
            context['username'] = username
            context['password'] = password
        return context


class IndexView(IndexLevelMixin, TemplateView):
    template_name = "main/index.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context_data = super().get_context_data(**kwargs)
        context_data["dates"] = list(FestivalDate.objects.order_by("day")[:2]) #テンプレートで多用するので、listにするとクエリ削減
        dt_now = timezone.now()

        performances_not_started = []
        performances_ended = []

        for p in Performance.objects.select_related("date"):
            if not (p.begin_at and p.end_at and p.date):
                continue  # 不備は除外

            perf_end = datetime.datetime.combine(
                p.date.begin_at.date(), p.end_at, tzinfo=datetime.timezone.utc
            )

            if perf_end > dt_now:
                performances_not_started.append(p)
            else:
                performances_ended.append(p)

        selected = []
        if len(performances_not_started) >= 4:
            # まだ終わっていない公演の中からランダムに4つ選ぶ
            selected = random.sample(performances_not_started, 4)
        else:
            # まずはまだ終わっていないものを全部追加
            selected = performances_not_started[:]
            # 不足分を過去のものからランダムに補充
            need = 4 - len(performances_not_started)
            if performances_ended:
                selected += random.sample(
                    performances_ended, min(need, len(performances_ended))
                )

        # 順番もランダム化
        random.shuffle(selected)
        context_data["performances"] = selected
        
        context_data["exhibitions"] = Exhibition.objects.order_by('?')[:4]
        context_data['news'] = News.objects.order_by('priority')

        festivaldate_obj = FestivalDate.objects.first()
        set_year = festivaldate_obj.begin_at.year
        context_data['slogan'] = Slogan.objects.filter(year=set_year).first()
        return context_data

class SlogansListView(IndexLevelMixin, ListView):
    # 過去含むスローガン一覧ビュー
    model = Slogan
    paginate_by = 20
    template_name = "main/slogan.html"
    context_object_name = "slogans"

    def get_context_data(self, **kwargs) -> dict:
        context_data = super().get_context_data(**kwargs)
        # year=NULLを除外しないと、空objをhtmlで参照してしまいエラーになる
        context_data["slogans"] = Slogan.objects.order_by("-year").exclude(year=None)
        return context_data


class About_DevelopmentView(IndexLevelMixin, TemplateView):
    template_name = "main/about_development.html"


class About_DesignView(IntroductionLevelMixin, TemplateView):
    template_name = "main/about_design.html"


class ExhibitionListView(IntroductionLevelMixin, ListView):
    """展示紹介用ビュー"""
    model = Exhibition
    paginate_by = 30
    template_name = "main/exhibition.html"
    category = None
    context_object_name = "exhibitions"

    def get_queryset(self) -> QuerySet[Any]:
        try:
            self.category = ExhibitionCategory(self.kwargs["category"])
        except ValueError:
            raise Http404()

        latest_review_status = Subquery(
            ExhibitionReviewReport.objects
                .filter(exhibition=OuterRef('pk'))
                .order_by('-reviewed_at')
                .values('status')[:1]
        )

        exhibitions = (
            Exhibition.objects
                .filter(category=self.category)
                .annotate(review_status=latest_review_status)
                .prefetch_related(
                    Prefetch(
                        'attractions',
                        queryset=Attraction.objects.order_by('-created_at'),
                        to_attr='ordered_attractions'
                    )
                )
                .prefetch_related("spots")
        )
        # 認証されていないユーザーには審査合格のみ表示
        if not self.request.user.has_perm('main.can_review_exhibition'):
            exhibitions = exhibitions.filter(
                review_status=ReviewReport.ReviewStatus.ACCEPTED
            )
        if self.category == ExhibitionCategory.CLASS:
            exhibitions = exhibitions.order_by('-grade_number', 'class_number')
        return exhibitions

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context_data = super().get_context_data(**kwargs)
        context_data["category"] = self.category
        return context_data

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        response = super().get(request, *args, **kwargs)
        if not self.category:
            return redirect("main:index")
        return response


class ExhibitionDetailView(UseTokenMixin, IntroductionLevelMixin, DetailView):
    template_name = "main/exhibition_detail.html"
    model = Exhibition
    context_object_name = "exhibition"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("tags", )


    def test_func(self) -> bool:
        permission = get_permission()
        self.object = self.get_object()
        token = self.request.session.get("edit_token")  # セッションから取得
        if self.request.user.is_superuser:
            return True
        elif self.request.user.has_perm('main.can_review_exhibition') \
            and self.request.user.has_perm('main.can_review_performance')\
            and self.request.user.has_perm('main.can_review_food_booth'):
            return True
        elif safe_token_compare(token, str(self.object.token)):
            # Token利用で、いつでもToken生徒は閲覧可能
            return True
        elif permission.display_introduction== True:
            return True
        else:
            return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object = self.get_object()
        token = self.request.session.get("edit_token")
        if  safe_token_compare(token, str(self.object.token)) or self.request.user.is_superuser:   #タイミング攻撃を考慮
            # 編集ページへ（token利用）
            # context['edit_url'] = reverse_lazy("main:exhibition_edit", kwargs={'pk': self.object.pk}) + "?token=" + str(self.object.token)
            context["token"] = str(self.object.token)
        context['success'] = self.request.session.pop('success', None)
        context['attraction'] = Attraction.objects.filter(exhibition=self.object).order_by("-created_at").first()
        return context


class ExhibitionReviewView(ReviewLevelMixin, DetailView):
    model = Exhibition
    template_name = 'main/exhibition_review.html'
    raise_exception = True
    permission_required = 'main.can_review_exhibition'

    def test_func(self) -> bool:
        if self.request.user.is_superuser:
            return True
        elif self.request.user.has_perm('main.can_review_exhibition'):
            return True
        else:
            return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reviews"] = ExhibitionReviewReport.objects.filter(exhibition=self.object)
        context["form"] = ExhibitionReviewForm(self.request.POST or None, initial={"exhibition": self.object})
        if self.request.user.is_superuser:
            context["token"] = str(self.object.token)
        return context
    
    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        self.object = self.get_object()
        context = self.get_context_data()
        
        form = ExhibitionReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.exhibition = self.object
            review.save()
            return HttpResponseRedirect(self.get_success_url())
        else:
            context['form'] = form
        
        return self.render_to_response(context)
    
    def get_success_url(self):
        self.request.session['success'] = True
        return reverse_lazy("main:mypage")


class ExhibitionEditView(UseTokenMixin, EditLevelMixin, UpdateView):
    template_name = "main/exhibition_edit.html"
    model = Exhibition
    form_class = ExhibitionForm
    
    def test_func(self) -> bool:
        if self.request.user.is_superuser:
            return True
        self.object = self.get_object()
        token = self.request.session.get("edit_token")  # セッションから取得
        students_can_edit_exhibitions = get_permission().can_edit_exhibitions and safe_token_compare(token, str(self.object.token))    #タイミング攻撃を考慮
        for report in self.object.review_reports.all(): # ただし、審査合格ならアクセス拒否
            if report.status == ReviewReport.ReviewStatus.ACCEPTED:
                return False
        return self.request.user.has_perm("change_exhibition") or students_can_edit_exhibitions

    def get_success_url(self) -> str:
        self.request.session['success'] = True
        # 編集が終わったらプレビューとしてDetailページへ（token利用）
        return reverse_lazy("main:exhibition_detail", kwargs={'pk': self.object.pk}) + "?token=" + str(self.object.token)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        data = self.request.POST if self.request.method == "POST" else None
        files = self.request.FILES if self.request.method == "POST" else None
        context["event_formset"] = EventFormSet(
            prefix="event",
            queryset=Event.objects.filter(
                exhibition=self.object
            ).prefetch_related(
                'exhibition',
                'spot',
                Prefetch(
                    'timeslots',
                    queryset=TimeSlot.objects.prefetch_related('date')
                ),
            ),
        )
        context["spots"] = self.object.spots.all()
        context["reviews"] = ExhibitionReviewReport.objects.filter(exhibition=self.object)
        return context

    def form_valid(self, exhibition_form: ExhibitionForm, event_formset):
        exhibition_obj = exhibition_form.save(commit=False)
        exhibition_obj.save()
        exhibition_form.save_m2m()

        for form in event_formset:
            obj = form.save(commit=False)
            obj.exhibition = exhibition_obj
            obj.save()
            
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, context):
        return self.render_to_response(context)

    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        if request.POST.get('form_action'):
            action = request.POST.get('form_action')
            if action == 'add_timeslot':
                return self.add_timeslot(request)
            elif action == 'delete_timeslot':
                return self.delete_timeslot(request)
            elif action == 'add_event':
                return self.add_event(request)
            elif action == 'delete_event':
                return self.delete_event(request)
            else:
                return HttpResponse("Invalid form action.", content_type="text/plain", status=400)
        
        self.object = self.get_object()
        context = self.get_context_data()
        
        form = self.get_form()
        data = self.request.POST if self.request.method == "POST" else None
        files = self.request.FILES if self.request.method == "POST" else None
        event_formset = EventFormSet(
            data=data,
            files=files,
            prefix="event",
        )

        if form.is_valid() and event_formset.is_valid():
            self.request.session['edit_done'] = True
            return self.form_valid(form, event_formset)
    
        return self.form_invalid(context)

    def add_timeslot(self, request: HttpRequest):
        event_pk = request.POST.get('event_pk')
        try:
            event = get_object_or_404(Event, pk=event_pk)
            event.timeslots.update_or_create(
                date = get_object_or_404(FestivalDate, pk=int(request.POST.get('date'))),
                begin_at = request.POST.get('begin_at'),
                end_at = request.POST.get('end_at')
            )
            rendered = render_to_string("main/partials/timeslots.html", {'timeslots': event.timeslots.all().prefetch_related("date")})
            response = {
                'success': True,
                'message': 'timeslot created successfully.',
                'timeslots_template': rendered,
            }
            return JsonResponse(response)
        except Exception as e:
            print(e)
            response = {
                'success': False,
                'message': 'failed to create timeslot.',
            }
            return JsonResponse(response)
    
    def delete_timeslot(self, request: HttpRequest):
        timeslot_pk = request.POST.get('timeslot_pk')
        try:
            timeslot = TimeSlot.objects.get(pk=timeslot_pk)
            timeslot.delete()
            response = {
                'success': True,
                'message': 'deleted the timeslot successfully.',
            }
            return JsonResponse(response)
        except TimeSlot.DoesNotExist:
            response = {
                'success': False,
                'message': 'No TimeSlot found with the given ID.',
            }
            return JsonResponse(response)
    
    def add_event(self, request: HttpRequest):
        try:
            exhibition = get_object_or_404(Exhibition, pk=int(self.kwargs["pk"]))
            event = Event(
                exhibition = exhibition,
                name = request.POST.get('name'),
                explanation = request.POST.get('explanation'),
                spot = get_object_or_404(Spot, pk=int(request.POST.get('spot'))),
                order = int(request.POST.get('order')),
            )
            event.full_clean()
            event.save()
            event_form = EventFormSet(
                prefix="event",
                queryset=Event.objects.filter(
                    exhibition=exhibition
                )
            )[-1]
            rendered = render_to_string('main/partials/event.html', {'event_form': event_form, 'index': int(request.POST.get('order')), 'spots': exhibition.spots.all()})
            response = {
                'success': True,
                'message': 'event created successfully.',
                'event_template': rendered,
            }
            return JsonResponse(response)
        except Exception as e:
            print(e)
            response = {
                'success': False,
                'message': 'failed to create an event.',
            }
            return JsonResponse(response)
    
    def delete_event(self, request: HttpRequest):
        event_pk = request.POST.get('event_pk')
        try:
            event = Event.objects.get(pk=event_pk)
            event.delete()
            response = {
                'success': True,
                'message': 'deleted the event successfully.',
            }
            return JsonResponse(response)
        except TimeSlot.DoesNotExist:
            response = {
                'success': False,
                'message': 'No Event found with the given ID.',
            }
            return JsonResponse(response)
    

class ExhibitionSearchView(IntroductionLevelMixin, ListView):
    # 検索で上手く一致するものが出てこないときは、permitedがTrueかどうかチェック！
    model = Exhibition
    template_name = 'main/exhibition_search.html'
    context_object_name = 'exhibitions' 
    paginate_by = 30
    form_class = ExhibitionSearchForm
    
    def get_queryset(self):
        queryset = Exhibition.objects.prefetch_related("tags", "spots")
        form = self.get_form()
        if form.is_valid():
            query = form.cleaned_data.get('query')
            selected_tags = form.cleaned_data.get('tags')

            query_filter = Q()
            if query:
                normalized_query = mojimoji.zen_to_han(query)
                wide_query = mojimoji.han_to_zen(query)
                # 入力されたクエリを全角から半角に変換＋半角でも全角に変換

                # スペースで区切る
                normalized_keywords = normalized_query.split()
                wide_keywords = wide_query.split()

                for keyword in (normalized_keywords + wide_keywords):
                    query_filter |= Q(
                        Q(title__icontains=keyword) |
                        Q(overview__icontains=keyword) |
                        Q(spots__name__icontains=keyword) |
                        Q(spots__floor__icontains=keyword) |
                        Q(tags__name=keyword)
                        # 検索範囲
                    )

            if selected_tags:
                query_filter |= Q(tags__in=selected_tags)

            queryset = Exhibition.objects.filter(query_filter).prefetch_related(
                Prefetch(
                    'attractions',
                    queryset=Attraction.objects.order_by('-created_at'),
                    to_attr='ordered_attractions'
                ), "spots",
            ).distinct()
        else:
            queryset = Exhibition.objects.none()

        return queryset

    def get_form(self):
        return ExhibitionSearchForm(self.request.GET or None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ExhibitionSearchForm(self.request.GET)
        form = self.get_form()
        if form.is_valid():
            context["valid_flag"] = True    #このフラグでテンプレートのメッセージを変える
        return context


class JumpToExhibitionsSearchView(IntroductionLevelMixin, ListView):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('query', '')
        query = unicodedata.normalize('NFKC', query)  # 全角数字を半角に正規化
        if query:
            search_url = f"{reverse('main:exhibitions_search')}?query={query}"
            return HttpResponseRedirect(search_url)
        # クエリが空の場合、元のページにリダイレクト（必要に応じて変更）
        return HttpResponseRedirect(reverse('main:exhibitions_search'))


class AttractionCreateView(UserPassesTestMixin, CreateView):
    """混雑度・待ち時間更新ビュー

    更新するごとに`Attraction`オブジェクトを作成する。
    
    """
    template_name = "main/attraction_create.html"
    model = Attraction
    form_class = AttractionForm
    
    def get_initial(self):
        initial = super().get_initial()
        latest_object = Attraction.objects.filter(exhibition=self.kwargs["pk"]).order_by('-created_at').first()
        self.latest_object = latest_object
        if latest_object:
            initial["congestion_level"] = latest_object.congestion_level
            initial["wait_time"] = latest_object.wait_time
            initial["announcement"] = latest_object.announcement
            initial["time_required"] = latest_object.time_required
            initial["ticket_status"] = latest_object.ticket_status
        return initial
    
    def dispatch(self, request, *args, **kwargs):   # ここは例外的にUseTokenMixinを使用しない
        token = request.GET.get('token')
        if token:
            request.session['exhibition_token'] = token
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        exhibition = get_object_or_404(Exhibition, pk=self.kwargs["pk"])
        permission = get_permission()
        token = self.request.session.get('exhibition_token')
        
        return self.request.user.is_superuser or (
            permission.can_edit_attractions and safe_token_compare(token, str(exhibition.token))
        )
    
    def handle_no_permission(self) -> HttpResponseRedirect:
        raise PermissionDenied
        
    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.exhibition = Exhibition.objects.get(pk=self.kwargs["pk"])
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())
    
    def get_success_url(self) -> str:
        self.request.session['success'] = True
        return reverse_lazy("main:attraction_create", kwargs={"pk": self.kwargs["pk"]})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['latest_object'] = self.latest_object
        if self.latest_object:  #オブジェクトがない場合エラーになる
            context['last_updated_at'] = self.latest_object.created_at.astimezone().strftime('%Y/%m/%d %H:%M:%S')
        context['exhibition'] = Exhibition.objects.get(pk=self.kwargs["pk"])
        context['success'] = self.request.session.pop('success', False)
        return context


class PerformanceListView(IntroductionLevelMixin, ListView):
    model = Performance
    template_name = "main/performance.html"
    context_object_name = "performances"

    def get_queryset(self) -> QuerySet[Any]:
        self.spot = get_object_or_404(Spot, pk=2)
        performances = Performance.objects.filter(spot=self.spot).prefetch_related(
            "songs", "members", "spot"
        ).order_by("date", "begin_at")
        return performances

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context_data = super().get_context_data(**kwargs)
        context_data["spot"] = self.spot
        context_data["title_name"] = "野外ライブ"
        context_data["dates"] = FestivalDate.objects.order_by("day")
        return context_data


class MusicRoomPerformanceListView(IntroductionLevelMixin, ListView):
    model = Performance
    template_name = "main/performance.html"
    context_object_name = "performances"

    def get_queryset(self) -> QuerySet[Any]:
        self.spot = get_object_or_404(Spot, pk=2)
        performances = Performance.objects.filter(spot__name="音楽室").prefetch_related(
            "songs", "members", "spot"
        ).order_by("begin_at")
        return performances

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context_data = super().get_context_data(**kwargs)
        context_data["spot"] = self.spot
        context_data["title_name"] = "音楽室ライブ"
        return context_data


class PerformanceDetailView(UseTokenMixin, IntroductionLevelMixin, DetailView):
    template_name = "main/performance_detail.html"
    model = Performance
    context_object_name = "performance"

    def test_func(self) -> bool:
        permission = get_permission()
        self.object = self.get_object()
        token = self.request.session.get("edit_token")  # セッションから取得
        if self.request.user.is_superuser:
            return True
        elif self.request.user.has_perm('main.can_review_exhibition') \
            and self.request.user.has_perm('main.can_review_performance')\
            and self.request.user.has_perm('main.can_review_food_booth'):
            return True
        elif safe_token_compare(token, str(self.object.token)):
            # Token利用で、いつでもToken生徒は閲覧可能
            return True
        elif permission.display_introduction== True:
            return True
        else:
            return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object = self.get_object()
        token = self.request.session.get("edit_token")
        if safe_token_compare(token, str(self.object.token)) or self.request.user.is_superuser:
            # 編集ページへ（token利用）
            # context['edit_url'] = reverse_lazy("main:performance_edit", kwargs={'pk': self.object.pk}) + "?token=" + str(self.object.token)
            context["token"] = str(self.object.token)
        context['success'] = self.request.session.pop('success', None)
        return context


class PerformanceReviewView(ReviewLevelMixin, DetailView):
    model = Performance
    template_name = 'main/performance_review.html'
    raise_exception = True
    permission_required = 'main.can_review_performance'

    def test_func(self) -> bool:
        if self.request.user.is_superuser:
            return True
        elif self.request.user.has_perm('main.can_review_performance'):
            return True
        else:
            return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reviews"] = PerformanceReviewReport.objects.filter(performance=self.object)
        context["form"] = PerformanceReviewForm(self.request.POST or None, initial={"performance": self.object})
        if self.request.user.is_superuser:
            context["token"] = str(self.object.token)
        return context
    
    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        self.object = self.get_object()
        context = self.get_context_data()
        
        form = PerformanceReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.performance = self.object
            review.save()
            return HttpResponseRedirect(self.get_success_url())
        else:
            context['form'] = form
        
        return self.render_to_response(context)
    
    def get_success_url(self):
        self.request.session['success'] = True
        return reverse_lazy("main:mypage")


class PerformanceEditView(UseTokenMixin, EditLevelMixin, UpdateView):
    model = Performance
    form_class = PerformanceForm
    template_name = "main/performance_edit.html"
    
    def test_func(self) -> bool:
        if self.request.user.is_superuser:
            return True
        self.object = self.get_object()
        token = self.request.session.get("edit_token")  # セッションから取得
        students_can_edit_performance = get_permission().can_edit_performances and safe_token_compare(token, str(self.object.token))
        for report in self.object.review_reports.all(): # ただし、審査合格ならアクセス拒否
            if report.status == ReviewReport.ReviewStatus.ACCEPTED:
                return False
        return self.request.user.has_perm("change_performances") or students_can_edit_performance

    def get_success_url(self) -> str:
        self.request.session['success'] = True
        # 編集が終わったらプレビューとしてDetailページへ（token利用）
        return reverse_lazy("main:performance_detail", kwargs={'pk': self.object.pk}) + "?token=" + str(self.object.token)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        data = self.request.POST if self.request.method == "POST" else None
        files = self.request.FILES if self.request.method == "POST" else None
        context["song_formset"] = SongFormSet(
            data=data,
            files=files,
            prefix="song",
            queryset=self.object.songs.all(),
        )
        context["member_formset"] = MemberFormSet(
            data=data,
            files=files,
            prefix="member",
            queryset=self.object.members.all(),
        )
        context["reviews"] = PerformanceReviewReport.objects.filter(performance=self.object)
        return context

    def form_valid(self, performance_form: PerformanceForm, song_formset, member_formset):
        self.object = performance_form.save(commit=False)
        self.object.save()
        performance_form.save_m2m()

        for form in song_formset:
            obj = form.save(commit=False)
            if form.cleaned_data['should_delete'] == True:
                Song.objects.get(pk=obj.pk).delete()
            else:
                obj.performance = self.object
                obj.save()
                form.save_m2m()
        for form in member_formset:
            obj = form.save(commit=False)
            if form.cleaned_data['should_delete'] == True:
                Member.objects.get(pk=obj.pk).delete()
            else:
                obj.performance = self.object
                obj.save()
                form.save_m2m()
        return HttpResponseRedirect(self.get_success_url())
    
    def form_invalid(self, context):
        return self.render_to_response(context)
    
    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        self.object = self.get_object() # 忘れずに
        context = self.get_context_data()
        
        form = self.get_form()
        data = self.request.POST if self.request.method == "POST" else None
        files = self.request.FILES if self.request.method == "POST" else None
        song_formset = SongFormSet(
            data=data,
            files=files,
            prefix="song",
        )
        member_formset = MemberFormSet(
            data=data,
            files=files,
            prefix="member",
        )

        if form.is_valid() and song_formset.is_valid() and member_formset.is_valid():
            return self.form_valid(form, song_formset, member_formset)

        return self.form_invalid(context)


class TimetableView(IntroductionLevelMixin, TemplateView):
    template_name = "main/timetable.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context_data = super().get_context_data(**kwargs)
        dates = FestivalDate.objects.order_by("day")
        day = self.kwargs["day"]
        today = dates.get(day=day)
        spots = Spot.objects.prefetch_related(
                "performances", "performances__date", "exhibitions", "events", "events__timeslots", "events__timeslots__date", "events__exhibition"
            ).annotate(
                has_event = Exists(Event.objects.filter(spot=OuterRef('pk'))),
                has_exhibition = Exists(Exhibition.objects.filter(spots__in=OuterRef('pk'))),
                has_performance = Exists(Performance.objects.filter(spot=OuterRef('pk'))),
            ).filter(
                Q(has_event=True) | Q(has_performance=True)
            ).order_by(
                "name", "-is_stage"
                )

        times = []
        time = today.begin_at
        # 表示用の時間枠を作っている
        while True:
            if time.timestamp() > today.end_at.timestamp():
                break
            times.append(time)
            time += datetime.timedelta(minutes=30)
        
        context_data["spots"] = spots
        context_data["times"] = times
        context_data["today"] = today
        context_data["dates"] = dates
        return context_data


class YouthSquareListView(IntroductionLevelMixin, ListView):
    model = FoodBooth
    template_name = "main/youthsquare.html"
    context_object_name = "food_booths"

    def get_queryset(self) -> QuerySet[Any]:
        return FoodBooth.objects.all()

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context_data = super().get_context_data(**kwargs)
        context_data["food_trucks"] = FoodTruck.objects.prefetch_related('spot', 'menus')
        
        return context_data

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if "spot_id" in self.kwargs:
            self.spot = get_object_or_404(Spot, pk=int(self.kwargs["spot_id"]))
            if not self.spot.is_stage:
                return redirect("main:index")
        
        return super().get(request, *args, **kwargs)


class FoodBoothEditView(UseTokenMixin, EditLevelMixin, UpdateView):
    template_name = "main/food_booth_edit.html"
    model = FoodBooth
    form_class = FoodBoothForm

    def test_func(self) -> bool:
        if self.request.user.is_superuser:
            return True
        self.object = self.get_object()
        token = self.request.session.get("edit_token")  # セッションから取得
        students_can_edit_exhibitions = get_permission().can_edit_foodbooth and safe_token_compare(token, str(self.object.token))
        for report in self.object.review_reports.all(): # ただし、審査合格ならアクセス拒否
            if report.status == ReviewReport.ReviewStatus.ACCEPTED:
                return False
        return self.request.user.has_perm("change_food_booth") or students_can_edit_exhibitions
    
    def get_success_url(self) -> str:
        self.request.session['success'] = True
        return reverse_lazy("main:food_booth_detail", kwargs={'pk': self.object.pk}) + "?token=" + str(self.object.token)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reviews"] = FoodBoothReviewReport.objects.filter(food_booth=self.object)
        return context


class FoodBoothReviewView(ReviewLevelMixin, DetailView):
    model = FoodBooth
    template_name = 'main/food_booth_review.html'
    context_object_name = "foodbooth"
    raise_exception = True
    permission_required = 'main.can_review_food_booth'

    def test_func(self) -> bool:
        if self.request.user.is_superuser:
            return True
        elif self.request.user.has_perm('main.can_review_food_booth'):
            return True
        else:
            return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reviews"] = FoodBoothReviewReport.objects.filter(food_booth=self.object)
        context["form"] = FoodBoothReviewForm(self.request.POST or None, initial={"food_booth": self.object})
        if self.request.user.is_superuser:
            context["token"] = str(self.object.token)
        return context
    
    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        self.object = self.get_object()
        context = self.get_context_data()
        
        form = FoodBoothReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.food_booth = self.object
            review.save()
            return HttpResponseRedirect(self.get_success_url())
        else:
            context['form'] = form
        
        return self.render_to_response(context)
    
    def get_success_url(self):
        self.request.session['success'] = True
        return reverse_lazy("main:mypage")
        

class FoodBoothDetailView(UseTokenMixin, IntroductionLevelMixin, DetailView):
    template_name = "main/foodbooth_detail.html"
    model = FoodBooth
    context_object_name = "foodbooth"

    def test_func(self) -> bool:
        permission = get_permission()
        self.object = self.get_object()
        token = self.request.session.get("edit_token")  # セッションから取得
        if self.request.user.is_superuser:
            return True
        elif self.request.user.has_perm('main.can_review_exhibition') \
            and self.request.user.has_perm('main.can_review_performance')\
            and self.request.user.has_perm('main.can_review_food_booth'):
            return True
        elif safe_token_compare(token, str(self.object.token)):
            # Token利用で、いつでもToken生徒は閲覧可能
            return True
        elif permission.display_introduction== True:
            return True
        else:
            return False
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.object = self.get_object()
        token = self.request.session.get("edit_token")
        if safe_token_compare(token, str(self.object.token)) or self.request.user.is_superuser:
            # 編集ページへ（token利用）
            # context['edit_url'] = reverse_lazy("main:food_booth_edit", kwargs={'pk': self.object.pk}) + "?token=" + str(self.object.token)
            context["token"] = str(self.object.token)
        context['success'] = self.request.session.pop('success', None)
        return context


class Egg(IndexLevelMixin,TemplateView):
    template_name = "main/egg.html"


class MapView(IntroductionLevelMixin, TemplateView):
    """セッションで"can_view_map"がTrueのときのみ閲覧可能
    """
    template_name = 'main/map.html'
    
    def test_func(self) -> bool:
        permission = get_permission()
        if self.request.user.is_authenticated:
            return True
        elif permission.map_key and self.request.session.get("map_key") == permission.map_key and permission.display_introduction== True:
            return True
        else:
            if self.request.session.get("map_key") != permission.map_key:
                self.request.session.pop("map_key", None)  # 合言葉が変わった場合に備えて、セッションから削除
                self.request.session.pop("can_view_map", None)
            return False

    def handle_no_permission(self):
        return redirect("main:map_auth")

    def get_requested_floor(self):
        # 要求された階数を取得し、数値に変換（デフォルトは7階）
        if "spot" in self.kwargs:
            spot_obj = get_object_or_404(Spot, pk=self.kwargs["spot"])
            return spot_obj.floor
        elif "floor" in self.kwargs:
            return int(self.kwargs["floor"])
        return 7

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        floor = self.get_requested_floor()
        if not Floor.validate(floor):
            raise Http404()

        # ===== Prefetch 定義 =====
        exhibitions_qs = (
            Exhibition.objects
            .only("id", "title", "category", "spots")
            .order_by("id")
        )

        performances_qs = (
            Performance.objects
            .only("id", "spot") #Performanceは1対1なのでspot
            .order_by("id")
        )

        spots_qs = (
            Spot.objects
            .filter(floor=floor)
            .prefetch_related(
                Prefetch(
                    "exhibitions",
                    queryset=exhibitions_qs,
                    to_attr="prefetched_exhibitions",
                ),
                Prefetch(
                    "performances",
                    queryset=performances_qs,
                    to_attr="prefetched_performances",
                ),
            )
        )

        # ===== spot 指定表示の場合 =====
        spot_id = self.request.GET.get("spot")
        if spot_id:
            try:
                spots_qs = spots_qs.annotate(
                    pin=Case(
                        When(id=int(spot_id), then=True),
                        default=False,
                        output_field=BooleanField(),
                    )
                )
            except ValueError:
                pass

        context.update({
            "all_spots": spots_qs,
            "floor": floor,
            "floor_name": Floor(floor).label,
            "path": f"main/img/maps/{floor}.webp",
            "map_key": get_permission().map_key,
        })

        if floor == 7:
            context["youthsquare_map_obj"] = YouthSquareMap.objects.first()
        return context
    

class MapAuthView(IntroductionLevelMixin, FormView):
    template_name = 'main/map_auth.html'
    form_class = MapKeyForm

    def form_valid(self, form):
        valid_map_key = get_permission().map_key
        end_date = FestivalDate.objects.order_by('-day').first()

        if not valid_map_key:
            form.add_error('key', 'システムエラーが発生しました。')
            return self.form_invalid(form)
        if form.cleaned_data['key'] != valid_map_key:
            form.add_error('key', '合言葉が間違っています。')
            return self.form_invalid(form)

        expires_in = int((end_date.end_at - timezone.now()).total_seconds())
        if expires_in <= 0:
            form.add_error('key', '文化祭が終了したため、校内地図は閲覧できません。')
            return self.form_invalid(form)

        self.request.session.cycle_key()
        self.request.session['can_view_map'] = True
        self.request.session['map_key'] = form.cleaned_data['key']
        self.request.session.set_expiry(expires_in)
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('main:map', kwargs={'floor': 7})
        
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["end_date"] = FestivalDate.objects.order_by('-day').first()
        return context


class QrcodeView(TemplateView):
    def get(self, request):
        url = request.GET.get('url')
        code = request.GET.get('_')
        if not (url and code):
            return HttpResponseForbidden()
        
        # らくなび以外のqrコードを生成させない
        match = False
        for host in settings.ALLOWED_HOSTS:
            if host in url:
                match = True
        if not match:
            return HttpResponseForbidden()
        parsed = urlparse(url)
        url = urlunparse(parsed._replace(query="")) #クエリパラメータを除去
        url = unquote(url)

        # QRコード生成
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="webp", quality=30, method=0)
        buffer.seek(0)

        return HttpResponse(buffer, content_type="image/webp")



class CreditsView(IntroductionLevelMixin, ListView):
    template_name = "main/credits.html"
    model = Credit

    def get_queryset(self):
        return Credit.objects.all()

    def get_context_data(self, **kwargs: Any):
        context = super().get_context_data(**kwargs)
        context['developers'] = self.get_queryset().filter(is_developer=True)
        context['contributors'] = self.get_queryset().filter(is_developer=False)
        return context

# エラーページの処理
def trigger_403(request):
    raise PermissionDenied()

def trigger_404(request):
    raise Http404()

def trigger_500(request):
    raise Exception("Triggered 500 Internal Server Error")

def trigger_400(reqest):
    raise SuspiciousOperation("Triggered 400 Bad Request")

def trigger_csrf_fail(request):
    # CSRFトークンなしでPOSTをシミュレート
    return HttpResponse("""
        <form method="POST">
            <!-- {% csrf_token %} を意図的に省略 -->
            <button type="submit">CSRFエラーを発生させる</button>
        </form>
    """)


def custom_403(request, exception):
    if exception:
        message = str(exception)
    # URLで分岐
    if request.path.startswith("/sports_fes/"):
        return render(request, 'sports_fes/error_pages/403.html', {'message': message}, status=403)
    elif request.path.startswith("/ya/"):
        return render(request, 'ya/error_pages/403.html', {'message': message}, status=403)
    return render(request, '403.html', {'message': message}, status=403)    #通常版

def custom_404(request, exception):
    # URLで分岐
    if request.path.startswith("/sports_fes/"):
        return render(request, 'sports_fes/error_pages/404.html', status=404)
    elif request.path.startswith("/ya/"):
            return render(request, 'ya/error_pages/404.html', status=404)
    return render(request, '404.html', status=404)

def custom_500(request):
    # URLで分岐
    if request.path.startswith("/sports_fes/"):
        return render(request, 'sports_fes/error_pages/500.html', status=500)
    elif request.path.startswith("/ya/"):
        return render(request, 'ya/error_pages/500.html', status=500)
    return render(request, '500.html', status=500)

def custom_400(request, exception):
    # URLで分岐
    if request.path.startswith("/sports_fes/"):
        return render(request, 'sports_fes/error_pages/400.html', status=400)
    elif request.path.startswith("/ya/"):
            return render(request, 'ya/error_pages/400.html', status=400)
    return render(request, '400.html', status=400)

def custom_csrf_fail(request, reason=""):
    # URLで分岐
    if request.path.startswith("/sports_fes/"):
        return render(request, 'sports_fes/error_pages/403_csrf.html', status=403)
    elif request.path.startswith("/ya/"):
            return render(request, 'ya/error_pages/403_csrf.html', status=403)
    return render(request, '403_csrf.html', status=403)


class ComingSoonView(TemplateView):
    template_name = "main/coming_soon.html"


def robots(request):
    content = (
        "#ねえねえロボットさん、あなたの見るこのファイルには、\n"
        "#イースターエッグが仕込まれることが多いんだって。\n"
        "#今日が、人間にとっていい一日になりますように。\n",
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "\n"
        "User-agent: Amazonbot\n"
        "Disallow: /\n"
        "User-agent: Applebot-Extended\n"
        "Disallow: /\n"
        "User-agent: Bytespider\n"
        "Disallow: /\n"
        "User-agent: CCBot\n"
        "Disallow: /\n"
        "User-agent: ClaudeBot\n"
        "Disallow: /\n"
        "User-agent: Google-Extended\n"
        "Disallow: /\n"
        "User-agent: GPTBot\n"
        "Disallow: /\n"
        "User-agent: meta-externalagent\n"
        "Disallow: /\n"
    )
    response = HttpResponse(content, content_type="text/plain; charset=utf-8")
    return response


class OfflineView(TemplateView):
    template_name = "main/offline.html"


class UnderReviewingView(TemplateView):
    template_name = "main/under_review.html"


class ManifestView(TemplateView):
    template_name = "main/manifest.json"
    content_type = "application/manifest+json"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # settings.py などから CDN の URL（プロトコル付き） を取得して渡す
        context["cdn_url"] = getattr(settings, 'CDN_DOMAIN_WITH_PROTOCOL', 'http://127.0.0.1:8000')
        return context


class FaviconView(View):
    def get(self, request, *args, **kwargs):
        # ファイルの絶対パスを取得
        path = os.path.join(settings.BASE_DIR, 'main', 'static', 'main', 'img', 'favicon.ico')
        
        # ファイルをバイナリ読み込みモードで開く
        response = FileResponse(open(path, 'rb'), content_type='image/x-icon')
        return response


class DocumentsListView(UserPassesTestMixin, TemplateView):
    template_name = "main/documents_list.html"

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        elif self.request.user.is_authenticated:
            if self.request.user.is_developer:  # is_developerを使う際はまずこれで分岐しないといけない
                return True
        else:
            return False

    def handle_no_permission(self):
        return HttpResponseForbidden()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        documents = list(Path('./docs/').glob('*.md')) #.mdファイルを取得
        context["documents"] = sorted(documents)    #アルファベット順
        return context


class DocumentsDetailView(UserPassesTestMixin, TemplateView):
    template_name = "main/document_detail.html"

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        elif self.request.user.is_authenticated:  # is_developerを使う際はまずこれで分岐しないといけない
            if self.request.user.is_developer:
                return True
        else:
            return False

    def handle_no_permission(self):
        return HttpResponseForbidden()

    def _replace_image_paths(self, html: str) -> str:
        cdn_base = settings.DOCS_IMAGES_URL

        def replacer(match):
            filename = match.group(1)  # "Screenshot From xxx.png" の部分（imagesフォルダ名を除く）
            return f'src="{cdn_base}/{filename}"'

        # ./images/xxx → cdn_base/xxx （"images/"は除去）
        return re.sub(r'src="\./images/([^"]+)"', replacer, html)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        path = next(Path("./docs/").glob(self.kwargs.get("name")), None)
        if path:
            with open(path, "r", encoding="UTF-8") as f:
                md_read = f.read()
                extensions = [
                    "extra",
                    "codehilite",
                    "sane_lists",
                    "toc",
                ]
                html = markdown.markdown(md_read, extensions=extensions)
            html = self._replace_image_paths(html)  # ← パス書き換え

            context["document"] = path
            context["html"] = html
        else:
            raise Http404()
        return context


class ReleaseNotesListView(UserPassesTestMixin, TemplateView):
    template_name = "main/release_notes_list.html"

    def test_func(self):
        if self.request.user.is_authenticated:
                if self.request.user.is_superuser or self.request.user.is_ya_user:
                    return True
        else:
            return False

    def handle_no_permission(self):
        return HttpResponseForbidden()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        documents = list(Path('./docs/releases/').glob('*.md')) #.mdファイルを取得
        context["documents"] = reversed(sorted(documents))    #逆アルファベット順
        return context


class ReleaseNotesDetailView(UserPassesTestMixin, TemplateView):
    template_name = "main/release_notes_detail.html"

    def test_func(self):
        if self.request.user.is_authenticated:
            if self.request.user.is_superuser or self.request.user.is_ya_user:
                    return True
        else:
            return False

    def handle_no_permission(self):
        return HttpResponseForbidden()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        path = next(Path("./docs/releases/").glob(self.kwargs.get("name")), None)    #urlで要求されたファイル名のパスを取得
        if path:
            with open(path, "r", encoding="UTF-8") as f:
                md_read = f.read()
                extentions = [  #HTML変換で有効にする機能
                    "extra",    #表とか一般的なやつ
                    "codehilite",   #コードブロック
                    "sane_lists", #リスト
                    "toc",  #目次
                ]
                html = markdown.markdown(md_read, extensions=extentions)   #変換
            context["document"] = path
            context["html"] = html
        else:
            raise Http404()
        return context


class ManualsForStudentsListView(UseTokenMixin, UserPassesTestMixin, TemplateView):
    template_name = "main/manuals_for_students_list.html"
    
    def test_func(self):
        Team = apps.get_model("sports_fes", "Team")
        if self.request.user.is_authenticated:
            return True
        token = self.request.session.get("edit_token")  # セッションから取得
        for exhibition in Exhibition.objects.all().only("token"):
            if safe_token_compare(token, exhibition.token):
                return True
        for foodbooth in FoodBooth.objects.all().only("token"):
            if safe_token_compare(token, foodbooth.token):
                return True
        for performance in Performance.objects.all().only("token"):
            if safe_token_compare(token, performance.token):
                return True
        for team in Team.objects.all().only("token"):
            if safe_token_compare(token, team.token):
                return True
        # 以上、いずれかに該当するTokenを所持していればアクセス可能、つまりコンテンツ作成者のみ
        return False #その他を明示
    
    def handle_no_permission(self):
        return HttpResponseForbidden()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        documents = list(Path('./docs/manuals_for_students/').glob('*.md')) #.mdファイルを取得
        context["documents"] = reversed(sorted(documents))    #逆アルファベット順
        return context


class ManualsForStudentsDetailView(UseTokenMixin, UserPassesTestMixin, TemplateView):
    template_name = "main/manual_for_students_detail.html"

    def test_func(self):
        if self.request.user.is_authenticated:
            return True
        token = self.request.session.get("edit_token")  # セッションから取得
        for exhibition in Exhibition.objects.all().only("token"):
            if token == exhibition.token:
                return True
        for foodbooth in FoodBooth.objects.all().only("token"):
            if token == foodbooth.token:
                return True
        for performance in Performance.objects.all().only("token"):
            if token == performance.token:
                return True
        # 以上、いずれかに該当するTokenを所持していればアクセス可能、つまりコンテンツ作成者のみ
        return False #その他を明示

    def handle_no_permission(self):
        return HttpResponseForbidden()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        path = next(Path("./docs/manuals_for_students/").glob(self.kwargs.get("name")), None)    #urlで要求されたファイル名のパスを取得
        if path:
            with open(path, "r", encoding="UTF-8") as f:
                md_read = f.read()
                extentions = [  #HTML変換で有効にする機能
                    "extra",    #表とか一般的なやつ
                    "codehilite",   #コードブロック
                    "sane_lists", #リスト
                    "toc",  #目次
                ]
                html = markdown.markdown(md_read, extensions=extentions)   #変換
            context["document"] = path
            context["html"] = html
        else:
            raise Http404()
        return context


# 以下、マイページ関連（今後views.py分割予定）


from io import BytesIO
from typing import Any
from django.db.models import OuterRef, Prefetch, Subquery
from django.db.models.base import Model as Model
from django.http import Http404,HttpRequest, HttpResponse
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.template.loader import render_to_string
import datetime, openpyxl
from urllib.parse import quote

from main.models import Exhibition, Performance, ExhibitionCategory, FoodBooth, ExhibitionReviewReport, PerformanceReviewReport, FoodBoothReviewReport, Spot

from rakunavi.utils import generate_qr_base64


#「説明会資料ダウンロード」で初期化した際のオブジェクト数
try:
    default_obj = DefaultCounts.objects.first()
    DEFAULT_LIVE_STAGE_COUNT = default_obj.live_stage_count
    DEFAULT_MUSIC_ROOM_COUNT = default_obj.music_room_count
except:
    DEFAULT_LIVE_STAGE_COUNT = 15
    DEFAULT_MUSIC_ROOM_COUNT = 5

DEFAULT_EXHIBITION_XLSX_PATH = "docs/展示一覧表.xlsx"


class MypageView(LoginRequiredMixin, TemplateView):
    template_name = "main/mypage.html"
    
    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['exhibitions'] = Exhibition.objects.annotate(
            review_status = Subquery(ExhibitionReviewReport.objects.filter(exhibition=OuterRef('pk')).order_by('-reviewed_at').values('status')[:1])
        )
        context['performances'] = Performance.objects.annotate(
            review_status = Subquery(PerformanceReviewReport.objects.filter(performance=OuterRef('pk')).order_by('-reviewed_at').values('status')[:1])
        )
        context['food_booths'] = FoodBooth.objects.annotate(
            review_status = Subquery(FoodBoothReviewReport.objects.filter(food_booth=OuterRef('pk')).order_by('-reviewed_at').values('status')[:1])
        )
        
        context['success'] = self.request.session.pop('success', False)
        return context
    
    def post(self, request: HttpRequest, *args: str, **kwargs: Any) -> HttpResponse:
        if self.request.POST.get('action') == 'review_pdf_download':
            return download_review_pdf(
                request = self.request,
                date=self.request.POST.get('date'),
                deadline=self.request.POST.get('deadline'),
                model=self.request.POST.get('model')
            )
        elif self.request.POST.get('action') == 'handout_pdf_download':
            if self.request.POST.get('init') == 'true':
                try:
                    init_objects(model=self.request.POST.get('model'))
                except Exception as error:
                    return HttpResponse(str(error), content_type="text/plain", status=400)
            return download_handout_pdf(
                request=self.request,
                date=self.request.POST.get('date'),
                deadline=self.request.POST.get('deadline'),
                model=self.request.POST.get('model')
            )
        else:
            return Http404()


def init_objects(model: str) -> None:
    # 先にバックアップを行う
    from scripts import backup_db
    backup_db.backup_db("auto_db")
    if model == 'exhibition':
        init_exhibition_objects()
    elif model == 'food_booth':
        init_food_booth_objects()
    elif model == 'live_stage_performance':
        init_performance_objects(count=DEFAULT_LIVE_STAGE_COUNT, spot=Spot.objects.get(name="野外ライブステージ"))
    elif model == 'music_room_performance':
        init_performance_objects(count=DEFAULT_MUSIC_ROOM_COUNT, spot=Spot.objects.get(name="音楽室"))
    else:
        raise ValueError(f"InvalidModel: {model}")


def init_exhibition_objects(xlsx_path: str | None = None) -> None:
    """展示オブジェクトを初期化する。全てのオブジェクトを削除し、空のオブジェクトを作成する。
    Args:
        xlsx_path (str | None): 展示一覧表のパス。Noneの場合はデフォルトのパスを使用する。
    """
    if xlsx_path is None:
        xlsx_path = DEFAULT_EXHIBITION_XLSX_PATH

    openpyxl_workbook = openpyxl.load_workbook(xlsx_path)

    exhibitions: list[Exhibition] = []
    
    for row in openpyxl_workbook[ExhibitionCategory.CLASS.label].iter_rows(min_row=2, max_row=19, max_col=5, values_only=True):
        grade_num, class_num, title, has_exhibition, has_food_booth = row
        if not (has_exhibition == "あり" and grade_num and class_num):
            continue
        title = f"高校{grade_num}年{class_num}組" # data_onlyはExcelで一回も開いてない場合は利用不可
        exhibitions.append(Exhibition(title=title, category=ExhibitionCategory.CLASS, grade_number=int(grade_num), class_number=int(class_num)))
    
    def create_exhibitions_from_sheet(category: ExhibitionCategory) -> None:
        for row in openpyxl_workbook[category.label].iter_rows(min_row=2, max_col=1, values_only=True):
            title = row[0]
            if not title:
                continue
            exhibitions.append(Exhibition(title=title, category=category))
    
    create_exhibitions_from_sheet(ExhibitionCategory.CLUB)
    create_exhibitions_from_sheet(ExhibitionCategory.GRADE)
    create_exhibitions_from_sheet(ExhibitionCategory.FACILITY)
    
    Exhibition.objects.all().delete()
    Exhibition.objects.bulk_create(exhibitions)
    

def init_food_booth_objects(xlsx_path: str | None = None) -> None:
    """模擬店オブジェクトを初期化する。全てのオブジェクトを削除し、空のオブジェクトを作成する。
    """
    if xlsx_path is None:
        xlsx_path = DEFAULT_EXHIBITION_XLSX_PATH
        
    openpyxl_workbook = openpyxl.load_workbook(xlsx_path)
    
    food_booths: list[FoodBooth] = []
    for row in openpyxl_workbook[ExhibitionCategory.CLASS.label].iter_rows(min_row=2, max_row=19, max_col=5, values_only=True):
        grade_num, class_num, title, has_exhibition, has_food_booth = row
        if not (has_exhibition == "あり" and grade_num and class_num and has_food_booth == "あり"):  # 学年・クラスが空の場合は飛ばす
            continue
        title = f"高校{grade_num}年{class_num}組" # data_onlyはExcelで一回も開いてない場合は利用不可
        food_booths.append(FoodBooth(name=title, grade_number=int(grade_num), class_number=int(class_num)))

    FoodBooth.objects.all().delete()
    FoodBooth.objects.bulk_create(food_booths)


def init_performance_objects(count: int, spot: Spot) -> None:
    """ライブオブジェクトを初期化する。全てのオブジェクトを削除し、空のオブジェクトを作成する。
    Args:
        count (int): 作成するライブの数
        spot (Spot): ライブの場所（野外ライブステージ, 音楽室）
    """
    Performance.objects.filter(spot=spot).delete()  # 既存のライブを削除
    performances: list[Performance] = []

    max_pk = Performance.objects.aggregate(Max('pk'))['pk__max'] or 0
    for i in range(count):
        performances.append(Performance(name=f"ライブ{i + max_pk}", spot=spot))
    Performance.objects.bulk_create(performances)


def download_handout_pdf(request:HttpRequest, date: str, deadline: str, model: str) -> HttpResponse:
    """らくなび説明会資料のPDFをダウンロードする
    Args:
        date (str): プリント配布日
        deadline (str): 編集期限
        model (str): 対象のモデル名（exhibition, live_stage_performance, music_room_performance）
    """
    context = {
        'date': datetime.datetime.fromisoformat(date.replace("Z", "+00:00")).astimezone(), # datetimeオブジェクトに変換
        'deadline': format_deadline(datetime.datetime.fromisoformat(deadline.replace("Z", "+00:00")).astimezone()), # stringに変換
        'objects': []
    }

    if model == 'exhibition':
        for exhibition in Exhibition.objects.all():
            relative_url__exhibition = reverse_lazy("main:exhibition_detail", kwargs={"pk": exhibition.pk}) + f'?token={exhibition.token}'
            absolute_url__exhibition = request.build_absolute_uri(relative_url__exhibition)
            relative_url__attraction = reverse_lazy("main:attraction_create", kwargs={"pk": exhibition.pk}) + f'?token={exhibition.token}'
            absolute_url__attraction = request.build_absolute_uri(relative_url__attraction)
            exhibition_dict = {
                "id": exhibition.pk,
                "title": exhibition.title,
                "category": exhibition.category,
                "grade_number": exhibition.grade_number,
                "class_number": exhibition.class_number,
                "qr_exhibition": generate_qr_base64(absolute_url__exhibition),
                "qr_attraction": generate_qr_base64(absolute_url__attraction),
            }
            context["objects"].append(exhibition_dict)
        return get_file_response("main/export/handout/exhibition.html", context)
    
    if model == 'food_booth':
        # exhibitionには紐づいていない
        # for food_booth in FoodBooth.objects.all().select_related('exhibition'):
        for food_booth in FoodBooth.objects.all():
            relative_url = reverse_lazy("main:food_booth_detail", kwargs={"pk": food_booth.pk}) + f'?token={food_booth.token}'
            absolute_url = request.build_absolute_uri(relative_url)
            food_booth_dict = {
                "id": food_booth.pk,
                "name": food_booth.name,
                "grade_number": food_booth.grade_number,
                "class_number": food_booth.class_number,
                "qr": generate_qr_base64(absolute_url),
            }
            context["objects"].append(food_booth_dict)
        return get_file_response("main/export/handout/food_booth.html", context)
    
    elif model == 'live_stage_performance':
        for performance in Performance.objects.filter(spot__name="野外ライブステージ").select_related('spot'):
            relative_url = reverse_lazy("main:performance_detail", kwargs={"pk": performance.pk}) + f'?token={performance.token}'
            absolute_url = request.build_absolute_uri(relative_url)
            context["objects"].append({
                "id": performance.id,
                "spot": performance.spot,
                "qr": generate_qr_base64(absolute_url),
            })
        return get_file_response("main/export/handout/performance.html", context)

    elif model == 'music_room_performance':
        for performance in Performance.objects.filter(spot__name="音楽室").select_related('spot'):
            relative_url = reverse_lazy("main:performance_detail", kwargs={"pk": performance.pk}) + f'?token={performance.token}'
            absolute_url = request.build_absolute_uri(relative_url)
            context["objects"].append({
                "id": performance.id,
                "spot": performance.spot,
                "qr": generate_qr_base64(absolute_url),
            })
        return get_file_response("main/export/handout/performance.html", context)

    else:
        return HttpResponse("InvalidModel", content_type="text/plain", status=400)


def download_review_pdf(request: HttpRequest, date: str, deadline: str, model: str) -> HttpResponse:
    """審査差し戻し内容のPDFをダウンロードする
    Args:
        date (str): プリント配布日
        deadline (str): 編集期限
        model (str): 対象のモデル名（exhibition, food_booth, live_stage_performance, music_room_performance）
    """
    context = {
        'date': datetime.datetime.fromisoformat(date.replace("Z", "+00:00")).astimezone(),
        'deadline': format_deadline(datetime.datetime.fromisoformat(deadline.replace("Z", "+00:00")).astimezone()),
        'objects': {}
    }

    def exhibition_context() -> None:
        for exhibition in Exhibition.objects.prefetch_related(
            Prefetch('review_reports', queryset=ExhibitionReviewReport.objects.order_by('-reviewed_at'))
        ):
            review: ExhibitionReviewReport | None = exhibition.review_reports.first()
            recipient = exhibition.title
            if exhibition.category == ExhibitionCategory.CLASS:
                recipient = f"高校{exhibition.grade_number}年{exhibition.class_number}組 {exhibition.title}"
            relative_url = reverse_lazy("main:exhibition_detail", kwargs={"pk": exhibition.pk}) + f'?token={exhibition.token}'
            absolute_url = request.build_absolute_uri(relative_url)
            relative_url__attraction = reverse_lazy("main:attraction_create", kwargs={"pk": exhibition.pk}) + f'?token={exhibition.token}'
            absolute_url__attraction = request.build_absolute_uri(relative_url__attraction)
            if review and review.status != "accepted":
                reason = review.reason
                qr = generate_qr_base64(absolute_url)
                qr__attraction = generate_qr_base64(absolute_url__attraction)
            else:
                reason = "なし"
                qr = ""
                qr__attraction = generate_qr_base64(absolute_url__attraction)

            context['objects'][exhibition.pk] = {
                'recipient': f"展示 ({recipient})",
                'reason': reason,
                "qr": qr,
                'qr__attraction' : qr__attraction,
                'in_charge_of' : review.in_charge_of if review else "Unnamed",
            }

    def food_booth_context() -> None:
        for food_booth in FoodBooth.objects.prefetch_related(
            Prefetch('review_reports', queryset=FoodBoothReviewReport.objects.order_by('-reviewed_at'))
        ):
            review: FoodBoothReviewReport | None = food_booth.review_reports.first()
            relative_url = reverse_lazy("main:food_booth_detail", kwargs={"pk": food_booth.pk}) + f'?token={food_booth.token}'
            absolute_url = request.build_absolute_uri(relative_url)

            if review and review.status != "accepted":
                reason = review.reason
                qr = generate_qr_base64(absolute_url)
            else:
                reason = "なし"
                qr = ""

            context['objects'][food_booth.pk] = {
                'recipient': f"模擬店 (高校{food_booth.grade_number}年{food_booth.class_number}組 {food_booth.name})",
                'reason': reason,
                "qr": qr,
                'in_charge_of' : review.in_charge_of if review else "Unnamed",
            }

    def performance_context(spot_name: str) -> None:
        for performance in Performance.objects.filter(spot__name=spot_name).prefetch_related(
            Prefetch('review_reports', queryset=PerformanceReviewReport.objects.order_by('-reviewed_at'))
        ):
            review: PerformanceReviewReport | None = performance.review_reports.first()

            if spot_name == "野外ライブステージ":
                live_type = "野外ライブ"
            elif spot_name == "音楽室":
                live_type = "音楽室ライブ"
            else:
                raise ValueError("InvalidSpotName: " + spot_name)

            relative_url = reverse_lazy("main:performance_detail", kwargs={"pk": performance.pk}) + f'?token={performance.token}'
            absolute_url = request.build_absolute_uri(relative_url)

            if review and review.status != "accepted":
                reason = review.reason
                qr = generate_qr_base64(absolute_url)
            else:
                reason = "なし"
                qr = ""

            context['objects'][performance.pk] = {
                'recipient': f"{live_type} ({performance.name})",
                'reason': reason,
                "qr": qr,
                'in_charge_of' : review.in_charge_of if review else "Unnamed",
            }

    if model == 'exhibition':
        exhibition_context()
    elif model == 'food_booth':
        food_booth_context()
    elif model == 'live_stage_performance':
        performance_context(spot_name="野外ライブステージ")
    elif model == 'music_room_performance':
        performance_context(spot_name="音楽室")

    return get_file_response("main/export/review/review.html", context)


def get_file_response(template_name: str, context: dict[str, Any], filename="document.pdf") -> HttpResponse:
    """PDFファイルをダウンロードするためのレスポンスを返す
    """
    if len(context['objects']) == 0:
        return HttpResponse("ObjectNotFound", content_type='text/plain', status=404)

    try:
        from weasyprint import HTML
    except OSError as e:
        error_text = 'サーバー環境（AWSのEC2インスタンス）で、Weasyprintに必要なライブラリがインストールされていない可能性があります。\nサーバー上のログに記載されているリンク ("WeasyPrint could not import some external libraries." の下部) を参考に、OSに応じて必要なライブラリをインストールしてください。'
        print(error_text)
        return HttpResponse(error_text, content_type="text/plain", status=500)

    html_string = render_to_string(template_name, context)
    html = HTML(string=html_string)
    
    pdf_file = BytesIO()
    html.write_pdf(target=pdf_file)
    pdf_file.seek(0)
    
    response = HttpResponse(pdf_file.read(), content_type='application/pdf')
    response["Content-Disposition"] = (
        f'attachment; filename="download.pdf"; '
        f"filename*=UTF-8''{quote(filename)}"
    )
    return response


def format_deadline(datetime: datetime.datetime) -> str:
    """フォーマットされた締切日時を返す関数
    Args:
        datetime (datetime): 締切日時
    """
    days = ["月", "火", "水", "木", "金", "土", "日"]
    formatted_date = f"{datetime.month}月{datetime.day}日({days[datetime.weekday()]}) {datetime.hour}時"
    if datetime.minute > 0:
        formatted_date += f"{datetime.minute}分"
    return formatted_date


# 以下は、CM出力
import io
from openpyxl import Workbook

class Download_cm_urls(LoginRequiredMixin, TemplateView):
    def get(self, reqest):
        # Excel作成
        wb = Workbook()
        ws = wb.active
        ws.title = "Exhibition CM URLs"

        # ヘッダ行
        ws.append(["学年・クラス", "タイトル", "CM動画URL"])

        exhibitions = Exhibition.objects.exclude(video_file="")
        for ex in exhibitions:
            url = ex.video_file.url if ex.video_file else ""
            if ex.grade_number and ex.class_number:
                grade_and_class = str(ex.grade_number)+"年"+str(ex.class_number)+"組"
            else:
                grade_and_class = ""
            ws.append([grade_and_class, ex.title, url])

        
        ws.append([""])
        ws.append(["CM提出があった展示のみ掲載しています。"])
        # メモリに保存
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        # ダウンロードレスポンス
        response = HttpResponse(
            output,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="Exhibitions_CM_URLs.xlsx"'
        return response
