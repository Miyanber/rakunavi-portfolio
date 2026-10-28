from django.urls import include, path

from allauth.account import views as account_views
from allauth.urls import build_provider_urlpatterns

from . import views

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='account_login'),
    path('logout/', account_views.logout, name='account_logout'),
    path('signup/', account_views.signup, name='account_signup'),
    path('inactive/', account_views.account_inactive, name='account_inactive'),
]

urlpatterns += build_provider_urlpatterns()
