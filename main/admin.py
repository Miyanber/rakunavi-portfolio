from typing import Any
from django.contrib import admin
from django.db import transaction
from django.db.models.query import QuerySet
from django.db.models import Prefetch
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, Permission
from django.http import HttpRequest
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import *
from .widgets import PreviewableFileInput

# トークンのリセット関数（先にバックアップは取る）
def reset_exhibition_token(modeladmin, request, queryset):
    from scripts import backup_db
    backup_db.backup_db("auto_db")  # バックアップ

    exhibitions = list(queryset)  # 選択されたものだけ対象にする
    for exhibition in exhibitions:
        # exhibition.token = uuid.uuid4()
        exhibition.token = generate_secure_token()
        exhibition.token_gen_datetime = timezone.now()
    with transaction.atomic():  # 一括更新でクエリ削減
        queryset.model.objects.bulk_update(exhibitions, ['token', 'token_gen_datetime'])
    
    print(f"{len(exhibitions)} 件の展示に新しいトークンを割り当てました。")
    messages.success(request, f"{len(exhibitions)} 件の展示に新しいトークンを割り当てました。")
reset_exhibition_token.short_description = "⚠展示のトークンをリセットする"

def reset_foodbooth_token(modeladmin, request, queryset):
    from scripts import backup_db
    backup_db.backup_db("auto_db")  # バックアップ
    
    foodbooths = list(queryset) # 選択されたものだけ対象にする
    for foodbooth in foodbooths:
        foodbooth.token = generate_secure_token()
        foodbooth.token_gen_datetime = timezone.now()
    with transaction.atomic():  # 一括更新でクエリ削減
        queryset.model.objects.bulk_update(foodbooths, ['token', 'token_gen_datetime'])
    
    print(f"{len(foodbooths)} 件の模擬店に新しいトークンを割り当てました。")
    messages.success(request, f"{len(foodbooths)} 件の模擬店に新しいトークンを割り当てました。")
reset_foodbooth_token.short_description = "⚠模擬店のトークンをリセットする"

def reset_performance_token(modeladmin, request, queryset):
    from scripts import backup_db
    backup_db.backup_db("auto_db")  # バックアップ
    
    performances = list(queryset)   # 選択されたものだけ対象にする
    for performance in performances:
        performance.token = generate_secure_token()
        performance.token_gen_datetime = timezone.now()
    with transaction.atomic():  # 一括更新でクエリ削減
        queryset.model.objects.bulk_update(performances, ['token', 'token_gen_datetime'])
    
    print(f"{len(performances)} 件のライブに新しいトークンを割り当てました。")
    messages.success(request, f"{len(performances)} 件のライブに新しいトークンを割り当てました。")
reset_performance_token.short_description = "⚠ライブのトークンをリセットする"


class PreviewableImageAdmin(admin.ModelAdmin):
    """画像のプレビュー機能を追加"""    
    
    formfield_overrides = {
        models.ImageField: {'widget': PreviewableFileInput()},
    }
    
    class Media:
        js = (
            "main/js/admin.js",
            "main/js/image_validate.js",
        )
        css = {
            'all': (
                'https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200',
            ),
        }

# Register your models here.
@admin.register(Exhibition)
class ExhibitionAdmin(PreviewableImageAdmin):
    list_display = ('title', 'overview', 'category', )
    search_fields = ('title', )
    ordering = ('id', )
    actions = [reset_exhibition_token]
    readonly_fields = ('token_gen_datetime', )
    

@admin.register(Spot)
class SpotAdmin(admin.ModelAdmin):
    list_display = ('name', 'floor')
    ordering = ('floor', 'name')


@admin.register(Attraction)
class AttractionAdmin(admin.ModelAdmin):
    # list_display = ('exhibition', )
    search_fields = ('exhibition__title', )
    actions = [reset_exhibition_token]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).prefetch_related(
            Prefetch('exhibition', queryset=Exhibition.objects.prefetch_related('spots')),
        )


@admin.register(Performance)
class PerformanceAdmin(PreviewableImageAdmin):
    list_display = ('name', 'begin_at', 'end_at', 'spot', )
    search_fields = ('name', )
    ordering = ('spot__name', 'begin_at',)
    actions = [reset_performance_token]
    readonly_fields = ('token_gen_datetime', )


@admin.register(Song)
class SongAdmin(admin.ModelAdmin):
    list_display = ('title', 'artist', 'performance', )
    search_fields = ('name', )
    ordering = ('performance__begin_at',)


@admin.register(Member)
class MemberAdmin(PreviewableImageAdmin):
    list_display = ('name', 'instrument', 'performance', )
    search_fields = ('name', )
    ordering = ('performance__name',)


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('date', 'begin_at', 'end_at', )
    ordering = ('date', 'begin_at',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'exhibition_title', 'spot', )
    search_fields = ('name', )
    ordering = ('exhibition__title',)
    list_select_related = ('exhibition', 'spot')
    
    def exhibition_title(self, obj):
        return obj.exhibition.title
    
    exhibition_title.short_description = '展示タイトル'


@admin.register(FoodBooth)
class FoodBoothAdmin(PreviewableImageAdmin):
    list_display = ('grade_number', 'class_number', 'name', 'price',)
    ordering = ('class_number', 'grade_number', )
    search_fields = ('name', )
    actions = [reset_foodbooth_token]
    readonly_fields = ('token_gen_datetime', )


@admin.register(FoodTruck)
class FoodTruckAdmin(PreviewableImageAdmin):
    list_display = ('name', )
    ordering = ('spot__name', )
    search_fields = ('name', )
    

@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'food_truck', )
    ordering = ('food_truck', )


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'priority')  # 管理画面で表示するフィールド
    search_fields = ('title', 'priority') 


@admin.register(ExhibitionReviewReport)
class ExhibitionReviewReportAdmin(admin.ModelAdmin):
    list_display = ('exhibition', 'reviewed_at', 'in_charge_of', 'status', 'reason')
    search_fields = ('exhibition__title', 'reason')
    ordering = ('-reviewed_at',)


@admin.register(PerformanceReviewReport)
class PerformanceReviewReportAdmin(admin.ModelAdmin):
    list_display = ('performance', 'reviewed_at', 'in_charge_of', 'status', 'reason')
    search_fields = ('performance__name', 'reason')
    ordering = ('-reviewed_at',)


@admin.register(FoodBoothReviewReport)
class FoodBoothReviewReportAdmin(admin.ModelAdmin):
    list_display = ('food_booth', 'reviewed_at', 'in_charge_of', 'status', 'reason')
    search_fields = ('food_booth__name', 'reason')
    ordering = ('-reviewed_at',)

@admin.register(ExhibitionTag)
class ExhibitionTagAdmin(admin.ModelAdmin):
    list_display = ('name', )
    search_fields = ('name', )
    ordering = ('id',)

@admin.register(Allergens)
class AllergensAdmin(admin.ModelAdmin):
    list_display = ('name', )
    search_fields = ('name', )
    ordering = ('id',)

@admin.register(YouthSquareMap)
class YouthSquareMap(admin.ModelAdmin):
    list_display = ("day1", "day2")
