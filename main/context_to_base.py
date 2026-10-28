# このファイルにはbase.htmlに渡したいデータを格納する（requestでもいいけど）
from config.models import Images, Slogan, Permission
from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone
from config.models import Slogan, Permission, FestivalDate, FeedBackFormURL
import datetime, subprocess
from urllib.parse import urlparse

from main.mixins import get_permission

from sports_fes.models import GeneralImages
from rakunavi import version

def common(request:HttpRequest) -> dict:
    # プロジェクト内共通
    context = {}
    # 現在のURL
    context["site_url"] = request.get_host()

    # Gitのブランチ名取得
    try:
        context["git_branch_name"] = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
            cwd=None,  # カレントディレクトリ
            stderr=subprocess.STDOUT,
            text=True).strip()
        context["git_hash"] = subprocess.run(
            "git show --format='%h' --no-patch",
            shell=True,
            capture_output=True,
            text=True,
        ).stdout
    except subprocess.CalledProcessError:
        context["git_branch_name"] = "Unknown"
        context["git_hash"] = "Unknown"

    context["rakunavi_version"] = version.RAKUNAVI_VERSION

    # クエリパラメータ除去したURL
    parsed = urlparse(request.build_absolute_uri())
    context["clean_url"] = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    context["feedback_form_url"] = FeedBackFormURL.objects.first().url  #オブジェクトはmigrateで必ず存在するのでエラーにならない
    context["session_edit_token"] = True if request.session.get("edit_token") else False  # セッションから取得、MainとSports_fesで使用
    return context

def main(request: HttpRequest) -> dict:
    # 文化祭アプリmainで使うものを想定（エラーページ含む）
    context = {}
    context["target_day"] = 1   #これだけは必要、エラーページも
    context["images"] = Images.objects.first()  #エラーページなどでも利用する
    # post_migrateでデフォルトで作成されるので、必ず1件は存在する
    context["config_permission"] = get_permission()

    if "sports_fes/" in request.path or "ya/" in request.path or "accounts/" in request.path:
        return context
    # Timetableで、2日目当日に、表示を2日目にする
    now = timezone.now()
    today = now.date()

    dates = list(FestivalDate.objects.order_by("day")[:2])

    if dates:
        set_year = dates[0].begin_at.year
        if len(dates) >= 2 and dates[1].begin_at.date() == today:
            context["target_day"] = 2
        if dates[1].end_at < timezone.now():
            context["festival_ended"] = True
    else:
        set_year = now.year
    
    context["slogan"] = Slogan.objects.filter(year=set_year).first()
    #context["footer_image_url"] = context["slogan"].footer_image.url if context["slogan"] else "" #urlのみ渡している。
    context["datetime_now_year"] = now.year

    context["deploy_done"] = settings.DEPLOY_DONE

    return context


def user_groups(request: HttpRequest) -> dict:
    """
    ユーザーが所属しているグループの名称一覧を取得するコンテキストプロセッサ

    コンテクストに`user_group_names`を追加します。
    """
    # ユーザのグループを取得
    if request.user.is_authenticated:
        groups = request.user.groups.all().values_list('name', flat=True)
        # グループ名をリストに変換
        groups = list(groups)
    else:
        groups = []
    
    return {
        'user_group_names': groups,
    }
