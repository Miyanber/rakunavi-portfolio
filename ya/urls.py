from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings

from main import views as main_views

from . import views

app_name = "ya"

urlpatterns = [
    # DM
    path("dms/", views.DirectMessagesListView.as_view(), name="dm_listview"),
    path("dm/<int:user_id>/", views.DirectMessageView.as_view(), name="dm"),
    path("dm/<int:user_id>/poll/", views.DirectMessagePollView.as_view(), name="dm_poll"),
    path("dm/<int:user_id>/read/", views.DirectMessageReadView.as_view(), name="dm_read"),
    # グループ
    path("group_chat/", views.GroupListView.as_view(), name="group_list"),
    path("group_chat/<int:group_id>/", views.GroupChatView.as_view(), name="group_chat"),
    path("group_chat/<int:pk>/settings/", views.GroupSettingsView.as_view(), name="group_settings"),
    path("groups/<int:group_id>/member/add/", views.group_member_add, name="group_member_add"),
    path("groups/<int:group_id>/member/remove/", views.group_member_remove, name="group_member_remove"),
    path("groups/create/", views.GroupQuickCreateView.as_view(), name="group_create"),

    # 投稿
    path("", views.PostsListView.as_view(), name="posts_listview"),
    path("posts/like/", views.toggle_like, name="toggle_like"),
    path("posts/<int:post_id>/delete/", views.post_delete, name="post_delete"),
    path("search/user/", views.SearchUserView.as_view(), name="search_user"),
    path("posts/<int:post_id>/", views.PostDetailView.as_view(), name="post_detail"),

    # 管理
    path("profile/edit/<str:user_id>/", views.UserInfoChangeView.as_view(), name="userinfo_change"),
    path('profile/<str:user_id>/', views.UserProfileView.as_view(), name='user_profile'),
    path("profile/password/change/", views.UserPasswordChangeView.as_view(), name="password_change"),

    # 通知
    path("notifications/", views.NotificationListView.as_view(), name="notification_list"),

    # 概要
    path("about_ya/", views.AboutView.as_view(), name="about_ya")
]

if settings.DEBUG:
    urlpatterns += [
        path("trigger_403/", main_views.trigger_403, name="trigger_403"),
        path("trigger_404/", main_views.trigger_404, name="trigger_404"),
        path("trigger_500/", main_views.trigger_500, name="trigger_500"),
        path("trigger_400/", main_views.trigger_400, name="trigger_400"),
        path("trigger_csrf", main_views.trigger_csrf_fail, name="trigger_csrf_fail"),
    ]
