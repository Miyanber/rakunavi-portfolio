#このファイルに権限管理を司るMixinたちがあります。
from colorama import init, Back, Fore, Style
init(autoreset=True) 
from django.core.cache import cache
from django.db.models.base import Model as Model
from django.db.models.signals import post_save, post_delete
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from allauth.account.views import LoginView
from django.template.loader import render_to_string
from django.dispatch import receiver

from config.models import Permission

from typing import Any


PERMISSION_CACHE_KEY = "permission_first"
PERMISSION_CACHE_TIMEOUT = 60 * 60  # 1時間

def get_permission():
    try:
        cached = cache.get(PERMISSION_CACHE_KEY)
        if cached is not None:
            return cached

        permission = Permission.objects.first()
        if permission is not None:
            cache.set(PERMISSION_CACHE_KEY, permission, PERMISSION_CACHE_TIMEOUT)
        return permission

    except Exception as e:
        print(Back.WHITE + Fore.RED + f"予期しない例外：{e}")
        print(Back.WHITE + Fore.RED + "get_permissionでPermissionのObject取得に失敗しました。")

# DB変更時キャッシュはクリア
@receiver(post_save, sender=Permission)
@receiver(post_delete, sender=Permission)
def reset_permission_cache(sender, **kwargs):
    cache.delete(PERMISSION_CACHE_KEY)


class IndexLevelMixin(UserPassesTestMixin):
    """
    Indexにおいて、権限を判別できるMixin
    
    """
    

    def test_func(self) -> bool:
        #スーパーユーザーは常時、ほかはpermission.display_homeがTrueのとき閲覧可能
        permission = get_permission()
        return self.request.user.is_authenticated or permission.display_home
        
    def handle_no_permission(self) -> HttpResponseRedirect:
        return redirect('main:coming_soon')
    

class IntroductionLevelMixin(UserPassesTestMixin):
    """
    展示紹介、ライブなどの紹介ページにおいて、権限を判別できるMixin、
    基本的にIndexLevelMixInと同じ
    
    """
    
    def test_func(self) -> bool:
        permission = get_permission()
        if self.request.user.is_superuser:
            return True
        elif self.request.user.has_perm('main.can_review_exhibition') \
            and self.request.user.has_perm('main.can_review_performance')\
            and self.request.user.has_perm('main.can_review_food_booth'):
            return True
        elif permission.display_introduction== True:
            return True
        else:
            return False
        
    def handle_no_permission(self) -> HttpResponseRedirect:
        return redirect('main:coming_soon')


class EditLevelMixin(UserPassesTestMixin):
    """
    編集ページおいて、権限を判別できるMixin、絶対にtest_func関数が必要
    
    ＊下は例、実際のページのViewでtest_funcを追加する
    def test_func(self) -> bool:
            permission = get_permission()
            token = self.request.GET.get('token')
            if self.request.user.is_superuser:
                return True
            elif self.request.user.groups.filter(name="教員用ユーザー").exists():
                return False
            else:
                try:
                    obj = self.get_object() #初期化
                except Exception:
                    return False
                return permission.can_edit_exhibitions and token == obj.token
    
    """
    raise_exception = True
    
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['success'] = self.request.session.pop('success', False)
        return context
    
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if self.request.user.is_superuser:
            self.test_func = lambda: True
        return super().dispatch(request, *args, **kwargs)
        
    def handle_no_permission(self) -> HttpResponseRedirect:
        return redirect("main:under_review")


class ReviewLevelMixin(PermissionRequiredMixin):
    """
    審査において、権限を判別できるMixin
    test_funcは以下のようにclass内に書く。

    def test_func(self) -> bool:
        if self.request.user.is_superuser:
            return True
        elif self.request.user.has_perm('main.can_review_exhibition') \
            and self.request.user.has_perm('main.can_review_performance')\
            and self.request.user.has_perm('main.can_review_food_booth'):
            return True
        else:
            return False
    """
    # page_type = None
        
    def handle_no_permission(self) -> HttpResponseRedirect:
        raise PermissionDenied


class AttractionLevelMixin(UserPassesTestMixin):
    """
    当日専用Attractionページで、権限を判別できるMixin、
    
    ＊現時点ではclass内に書いている
    """
        
    def handle_no_permission(self) -> HttpResponseRedirect:
        raise PermissionDenied


class Sports_FesIntroductionLevelMixin(UserPassesTestMixin):
    """
    体育祭アプリで、権限を判別できるMixin、
    
    """
    def test_func(self) -> bool:
        permission = get_permission()
        if self.request.user.is_superuser:
                return True
        return permission.display_sports_fes
        
    def handle_no_permission(self) -> HttpResponseRedirect:
        return redirect('sports_fes:coming_soon')


class UseTokenMixin():
    """
    Tokenを利用する場合、取得しセッションに保持させるためのMixin
    毎回セッション保存のtokenを上書きする
    """
    def dispatch(self, request, *args, **kwargs):
        token = self.request.GET.get("token")
        if token:
            self.request.session.cycle_key()    # セッションIDを再生成してセッション攻撃を防ぐ
            self.request.session["edit_token"] = token  # トークンはセッションに保持
            request.session.set_expiry(0) # ブラウザを閉じれば破棄
        return super().dispatch(request, *args, **kwargs)
