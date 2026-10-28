from django.conf import settings
from django.urls import path, include
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView

from . import views
from config import views as config_views

app_name = "main"
urlpatterns = [
    # できる限りクラスベースビューを使用
    path("", views.IndexView.as_view(), name="index"),
    path("slogans/", views.SlogansListView.as_view(), name="slogans"),

    path("about_development/", views.About_DevelopmentView.as_view(), name="about_development"),
    path("about_design/", views.About_DesignView.as_view(), name="about_design"),
    path("egg/", views.Egg.as_view(), name="egg"),
    path("credits/", views.CreditsView.as_view(), name="credits"),
    
    path("exhibitions_search/", views.ExhibitionSearchView.as_view(), name="exhibitions_search"),
    path('jump_to_exhibition_search/', views.JumpToExhibitionsSearchView.as_view(), name='jump_to_exhibitions_search'),

    path("exhibitions/<str:category>/", views.ExhibitionListView.as_view(), name="exhibitions"),
    path("exhibitions/detail/<int:pk>/", views.ExhibitionDetailView.as_view(), name="exhibition_detail"),

    path("exhibitions/attraction/create/<int:pk>/", views.AttractionCreateView.as_view(), name="attraction_create"),
    
    path("timetable/<int:day>/", views.TimetableView.as_view(), name="timetable"),
    
    path("youthsquare/food_booth/", views.YouthSquareListView.as_view(), name="youthsquare"),
    path("youthsquare/food_booth/detail/<int:pk>/", views.FoodBoothDetailView.as_view(), name="food_booth_detail"),
    path("youthsquare/outdoor_performance/", views.PerformanceListView.as_view(), name="outdoor_performances"),
    path("youthsquare/indoor_performance/", views.MusicRoomPerformanceListView.as_view(), name="indoor_performances"),
    path("youthsquare/performance/detail/<int:pk>/", views.PerformanceDetailView.as_view(), name="performance_detail"),

    path("management/", views.MypageView.as_view(), name="mypage"),
    path("management/download/cm-urls/", views.Download_cm_urls.as_view(), name="download_cm_urls"),

    # 編集
    path("management/edit/exhibition/<int:pk>/", views.ExhibitionEditView.as_view(), name="exhibition_edit"),
    path("management/edit/performance/<int:pk>/", views.PerformanceEditView.as_view(), name="performance_edit"),
    path("management/edit/food_booth/<int:pk>/", views.FoodBoothEditView.as_view(), name="food_booth_edit"),
    # 審査
    path("management/review/exhibition/<int:pk>/", views.ExhibitionReviewView.as_view(), name="exhibition_review"),
    path("management/review/performance/<int:pk>/", views.PerformanceReviewView.as_view(), name="performance_review"),
    path("management/review/food_booth/<int:pk>/", views.FoodBoothReviewView.as_view(), name="food_booth_review"),
    path("management/under_review_error/", views.UnderReviewingView.as_view(), name="under_review"),
    # ドキュメント
    path("management/documents/", views.DocumentsListView.as_view(), name="documents_list"),
    path("management/documents/<str:name>/", views.DocumentsDetailView.as_view(), name="document_detail"),
    # リリースノート
    path("management/release_notes/", views.ReleaseNotesListView.as_view(), name="release_notes_list"),
    path("management/release_notes/<str:name>/", views.ReleaseNotesDetailView.as_view(), name="release_notes_detail"),
    # 生徒用マニュアル
    path("management/manuals_for_students/", views.ManualsForStudentsListView.as_view(), name="manuals_for_students_list"),
    path("management/manuals_for_students/<str:name>/", views.ManualsForStudentsDetailView.as_view(), name="manuals_for_students_detail"),
    
    path("map_auth/", views.MapAuthView.as_view(), name="map_auth"),
    path("map/<int:floor>/", views.MapView.as_view(), name="map"),
    path("qrcode/", views.QrcodeView.as_view(), name="qrcode"),

    path("coming_soon/", views.ComingSoonView.as_view(), name="coming_soon"),
    path("offline/", views.OfflineView.as_view(), name="offline"),
    # robots.txt　ここは/入れない
    path('robots.txt', views.robots, name="robots"),
    path("manifest.json", views.ManifestView.as_view(), name="manifest"),
    path("favicon.ico", views.FaviconView.as_view(), name="favicon"),

    path("system_monitor/", config_views.SystemMonitorView.as_view(), name="system_monitor"),
    path("system_stats/", config_views.system_stats, name="system_stats"),  #取得用
    path("ec2_operations/", config_views.GitOperationsView.as_view(), name="ec2_operations")
]

if settings.DEBUG:
    urlpatterns += [
        path("trigger_403/", views.trigger_403, name="trigger_403"),
        path("trigger_404/", views.trigger_404, name="trigger_404"),
        path("trigger_500/", views.trigger_500, name="trigger_500"),
        path("trigger_400/", views.trigger_400, name="trigger_400"),
        path("trigger_csrf", views.trigger_csrf_fail, name="trigger_csrf_fail"),
    ]
