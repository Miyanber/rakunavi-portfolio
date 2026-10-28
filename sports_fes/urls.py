from django.conf import settings
from django.urls import path
from sports_fes import views
from main import views as main_views
app_name = 'sports_fes'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('program/', views.ProgramListView.as_view(), name='program_list'),
    path("programs/<int:number>/", views.ProgramDetailView.as_view(), name="program_detail"),
    
    path('team/', views.TeamView.as_view(), name='team'),
    path("management/edit/team/<int:pk>/", views.TeamInfoUpdateView.as_view(), name="team_info_update"),
    path("management/edit/team/print/", views.download_team_qr_pdf, name="team_info_print"),

    path('facilities/', views.FacilitiesView.as_view(), name='facilities'),
    path('access/', views.AccessView.as_view(), name='access'),

    path("credits/", views.CreditsView.as_view(), name="credits"),

    path("coming_soon/", views.ComingSoonView.as_view(), name="coming_soon"),
    path("slogans/", views.SlogansListView.as_view(), name="slogans"),

    path("developer_portal/", views.DeveloperportalView.as_view(), name="developer_portal")
]

if settings.DEBUG:
    urlpatterns += [
        path("trigger_403/", main_views.trigger_403, name="trigger_403"),
        path("trigger_404/", main_views.trigger_404, name="trigger_404"),
        path("trigger_500/", main_views.trigger_500, name="trigger_500"),
        path("trigger_400/", main_views.trigger_400, name="trigger_400"),
        path("trigger_csrf", main_views.trigger_csrf_fail, name="trigger_csrf_fail"),
    ]

urlpatterns += [
    path("preview_403/", views.preview_403, name="preview_403"),
    path("preview_404/", views.preview_404, name="preview_404"),
    path("preview_500/", views.preview_500, name="preview_500"),
    path("preview_400/", views.preview_400, name="preview_400"),
    path("preview_csrf/", views.preview_csrf, name="preview_csrf"),
]
