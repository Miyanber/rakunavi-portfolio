from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from django.utils import timezone

from main.models import *
from config.models import Permission as ConfigPermission, Slogan, FestivalDate

import inspect, datetime

# デフォルトの権限グループとその権限のマッピング
# ここで定義された権限は、models.pyのMetaクラスのpermissionsに記載すること
# で、マイグレーション時に自動的に作成される
DEFAULT_GROUPS = {
    "教員用ユーザー": [
        "can_review_exhibition",
        "can_review_performance",
        "can_review_food_booth",
        "can_download_exhibition_review",
        "can_download_performance_review",
        "can_download_food_booth_review",
    ],
}


def create_default_groups(sender, **kwargs):
    """
    デフォルトの権限グループ（django.contrib.auth.Group）を作成する
    """

    for group_name, permissions in DEFAULT_GROUPS.items():
        group, created = Group.objects.get_or_create(name=group_name)
        permissions = Permission.objects.filter(codename__in=permissions)
        group.permissions.add(*permissions)
        if created:
            print(inspect.currentframe().f_code.co_name, "：デフォルト設定のGroupを作成しました。")


def create_default_allergens(sender, **kwargs):
    """
    デフォルトの28品目のアレルゲンObjectを作成する
    """
    if Allergens.objects.exists():
        pass
    else:
        allergens_list = [
           'えび', 'かに', 'くるみ', '小麦', 'そば', '卵', '乳', '落花生（ピーナッツ）', 'アーモンド', 'あわび', 'いか', 'いくら', 'オレンジ', 'カシューナッツ', \
            'キウイフルーツ', '牛肉', 'ごま', 'さけ', 'さば', '大豆', '鶏肉', 'バナナ', '豚肉', 'マカダミアナッツ', 'もも', 'やまいも', 'りんご', 'ゼラチン'
            ]
        with transaction.atomic():
            for allergen in allergens_list:
                Allergens.objects.create(name=allergen)
            print(inspect.currentframe().f_code.co_name, "：デフォルト設定のmain.Allergensを作成しました。")


# 登録したのでappsでの呼び出しは不要
@receiver(m2m_changed, sender=Exhibition.spots.through)
def sync_floor_tags(sender, instance, action, **kwargs):
    """
    Exhibition と Spot の紐付けが変更されたら階タグを同期する
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        # --- 1. 既存の階タグを削除（他のタグは消さない） ---
        floor_labels = [Floor(f).label for f, _ in Floor.choices]
        instance.tags.remove(*ExhibitionTag.objects.filter(name__in=floor_labels))

        # --- 2. 現在の Spot から階タグを再追加 ---
        for spot in instance.spots.all():
            if spot.floor is not None:
                floor_label = Floor(spot.floor).label
                tag, _ = ExhibitionTag.objects.get_or_create(name=floor_label)
                instance.tags.add(tag)


# 審査後に編集を許可する場合は以下を有効にする。→審査後に上書きされても大丈夫になる
# @receiver(post_save, sender=Exhibition)
# def create_profile(sender, instance, created, **kwargs):
#     latest_review = instance.review_reports.last()
#     if latest_review:
#         if latest_review.reviewed_at < instance.updated_at:
#             # 審査後編集
#             ExhibitionReviewReport.objects.create(
#                 status = ReviewReport.ReviewStatus.PENDING,
#                 reason = "審査後に編集されたため、システムによって上書きされました。",
#                 exhibition = instance,
#                 in_charge_of = "らくなびシステム",
#             )

# @receiver(post_save, sender=Performance)
# def create_profile(sender, instance, created, **kwargs):
#     latest_review = instance.review_reports.last()
#     if latest_review:
#         if latest_review.reviewed_at < instance.updated_at:
#             # 審査後編集
#             PerformanceReviewReport.objects.create(
#                 status = ReviewReport.ReviewStatus.PENDING,
#                 reason = "審査後に編集されたため、システムによって上書きされました。",
#                 performance = instance,
#                 in_charge_of = "らくなびシステム",
#             )

# @receiver(post_save, sender=FoodBooth)
# def create_profile(sender, instance, created, **kwargs):
#     latest_review = instance.review_reports.last()
#     if latest_review:
#         if latest_review.reviewed_at < instance.updated_at:
#             # 審査後編集
#             FoodBoothReviewReport.objects.create(
#                 status = ReviewReport.ReviewStatus.PENDING,
#                 reason = "審査後に編集されたため、システムによって上書きされました。",
#                 food_booth = instance,
#                 in_charge_of = "らくなびシステム",
#             )
