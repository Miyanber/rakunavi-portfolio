from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import *


# Register your models here.
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'user_id',)
    ordering = ('user_id', )
    
    fieldsets = (
        (None, {"fields": ("user_id", "username", "password")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_ya_user",
                    "is_developer",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
        (_("Яの設定"), {"fields": ("friends", "icon", "header_image", "role", "self_introduction")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("user_id", "username", "usable_password", "password1", "password2", "role", ),
            },
        ),
    )

@admin.register(Slogan)
class SloganAdmin(admin.ModelAdmin):
    list_display = [
        'year', 'main', 'sub'
    ]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = [
        'display_home', 'display_introduction', 'display_sports_fes', 'can_edit_exhibitions', 'can_edit_performances', 'can_edit_attractions', 'can_edit_foodbooth', 'map_key'
    ]
    fieldsets = (
        ['表示', {"fields" : ('display_home', 'display_introduction', )}], 
        ['体育祭', {"fields": ('display_sports_fes', 'can_edit_team_info')}],
        ['編集', {"fields" : ('can_edit_exhibitions', 'can_edit_attractions', 'can_edit_performances', 'can_edit_foodbooth', )}],
        ['スケジュールによる変更（展示）', {"fields" : ('exhibitions_editing_deadline', 'exhibitions_editing_deadline_scheduled')}],
        ['スケジュールによる変更（模擬店）', {"fields" : ('food_booths_editing_deadline', 'food_booths_editing_deadline_scheduled',)}],
        ['スケジュールによる変更（ライブ）', {"fields" : ('performances_editing_deadline', 'performances_editing_deadline_scheduled',)}],
        ['スケジュールによる変更（公開・当日設定）', {"fields" : ('publishing_datetime', 'publishing_datetime_scheduled','allow_attraction_create_datetime', 'allow_attraction_create_datetime_scheduled')}],
        ['BETA状態', {"fields" : ('beta_status', )}],
        ['Map合言葉', {"fields" : ('map_key', )}],
    )
    # 追加ボタン非表示
    def has_add_permission(self, request):
        return False
    # 削除ボタンも非表示
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(FestivalDate)
class FestivalDateAdmin(admin.ModelAdmin):
    list_display = ('day', 'begin_at', 'end_at')
    search_fields = ('day', 'begin_at', 'end_at')


@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_developer',  'contribution', 'words']


@admin.register(Images)
class ImagesAdmin(admin.ModelAdmin):
    list_display = ['header_index']

@admin.register(DefaultCounts)
class DefaultCountsAdmin(admin.ModelAdmin):
    list_display = ['live_stage_count', 'music_room_count']

@admin.register(EC2OperationsLog)
class EC2OperationsLogAdmin(admin.ModelAdmin):
    list_display = ['datetime', 'user', 'command', 'exit_code', 'log_level']
    search_fields = ['datetime', 'user', 'command', 'response', ]

@admin.register(FeedBackFormURL)
class FeedBackFormURLAdmin(admin.ModelAdmin):
    list_display = ['id', 'url']

    # 追加ボタン非表示
    def has_add_permission(self, request):
        return False
    # 削除ボタンも非表示
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Sports_FesInfo)
class Sports_FesInfoAdmin(admin.ModelAdmin):
    list_display = ["year", "main", "sub"]

@admin.register(NewDomainRedirectURL)
class NewDomainRedirectURLAdmin(admin.ModelAdmin):
    list_display = ["url", "active"]

    # 追加ボタン非表示
    def has_add_permission(self, request):
        return False
    # 削除ボタンも非表示
    def has_delete_permission(self, request, obj=None):
        return False
