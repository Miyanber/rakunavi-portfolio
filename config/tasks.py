from apscheduler.schedulers.background import BackgroundScheduler
from colorama import init, Back, Fore, Style
init(autoreset=True) 
from django.utils import timezone

from main.mixins import get_permission
from scripts.backup_db import backup_db


# 管理設定を変更
def auto_change_permissions():
    now = timezone.now()
    permission = get_permission()
    db_updated = False

    # 展示の編集期限
    if (
        permission.exhibitions_editing_deadline
        and permission.exhibitions_editing_deadline < now
        and permission.exhibitions_editing_deadline_scheduled
    ):
        permission.can_edit_attractions = False
        permission.can_edit_exhibitions = False
        permission.exhibitions_editing_deadline_scheduled = False
        db_updated = True

    # 模擬店
    if (
        permission.food_booths_editing_deadline
        and permission.food_booths_editing_deadline < now
        and permission.food_booths_editing_deadline_scheduled
    ):
        permission.can_edit_foodbooth = False
        permission.food_booths_editing_deadline_scheduled = False
        db_updated = True

    # ライブ
    if (
        permission.performances_editing_deadline
        and permission.performances_editing_deadline < now
        and permission.performances_editing_deadline_scheduled
    ):
        permission.can_edit_performances = False
        permission.performances_editing_deadline_scheduled = False
        db_updated = True

    # 自動公開
    if (
        permission.publishing_datetime
        and permission.publishing_datetime < now
        and permission.publishing_datetime_scheduled
    ):
        permission.display_home = True
        permission.display_introduction = True
        permission.beta_status = False
        permission.publishing_datetime_scheduled = False
        db_updated = True

    # 展示当日ページ
    if (
        permission.allow_attraction_create_datetime
        and permission.allow_attraction_create_datetime < now
        and permission.allow_attraction_create_datetime_scheduled
    ):
        permission.can_edit_attractions = True
        permission.allow_attraction_create_datetime_scheduled = False
        db_updated = True

    if db_updated:
        print(Back.WHITE + Fore.RED + "[auto_change_permissions]: 管理設定をを変更しました。")
        permission.save()

# 開始用関数
def start():
    scheduler = BackgroundScheduler()
    # 自動管理設定変更
    scheduler.add_job(
            auto_change_permissions,
            "interval",
            minutes=1,
            id="auto_change_permissions",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60*30 #実行のずれを許容する時間[秒]
        )
    # 自動DBバックアップ
    scheduler.add_job(
        backup_db,
            "cron",
            hour=2, #毎日午前2時に自動実行
            id="backup_db",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60*60
        )
    scheduler.start()
