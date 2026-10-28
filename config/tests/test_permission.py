from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
User = get_user_model()
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from urllib.parse import urlencode


from config.models import Permission
from main.models import *


class TestPermissionCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        Permission.objects.all().delete()   #権限をリセット
        cls.permission = Permission.objects.create(
            id=1,
            display_home=False,
            display_introduction=False,
            display_sports_fes=False,
            can_edit_exhibitions=False,
            can_edit_performances=False,
            can_edit_attractions=False,
            can_edit_foodbooth=False,
            beta_status=False,
            exhibitions_editing_deadline=timezone.now(),
            exhibitions_editing_deadline_scheduled=False,
            food_booths_editing_deadline=timezone.now(),
            food_booths_editing_deadline_scheduled=False,
            performances_editing_deadline=timezone.now(),
            performances_editing_deadline_scheduled=False,
            publishing_datetime=timezone.now(),
            publishing_datetime_scheduled=False,
            allow_attraction_create_datetime=timezone.now(),
            allow_attraction_create_datetime_scheduled=False,
        )
        # スーパーユーザー
        cls.superuser = User.objects.create_user(
            username="superuser_xyz000",
            password="@random*0**",
            user_id="U0000",    #こっちを認証では利用
            is_superuser = True,
            is_staff =True,
        )
        # 一般ユーザー
        cls.auth_user = User.objects.create_user(
            username="xyz000",
            password="@random*0**",
            user_id="U0001", 
        )
        # 教員ユーザー（審査
        cls.teacher_user = User.objects.create_user(
            username="teacher_xyz000",
            password="@random*0**",
            user_id="U0002",
        )
        teacher_group = Group.objects.get(name="教員用ユーザー")
        cls.teacher_user.groups.add(teacher_group)  #グループに追加
        # Яユーザー
        cls.ya_user = User.objects.create_user(
            username="xyz001",
            password="@random*0**",
            user_id="U0003",
            is_ya_user =True 
        )

        # 展示
        Exhibition.objects.all().delete()
        Exhibition.objects.create(
            title = "This is for a test",
            category = ExhibitionCategory.CLASS,
            grade_number = 3,
            class_number = 10,
        )

    def test_superuser(self):
        self.permission.display_home = False
        self.permission.display_introduction = False
        self.permission.display_sports_fes = False
        self.permission.save()
        self.client.login(username="U0000", password="@random*0**")
        res = self.client.get(reverse("main:index"))    #ホーム
        self.assertEqual(res.status_code, 200)
        res = self.client.get(reverse("main:exhibitions", kwargs={"category": "class"}))    #展示
        self.assertEqual(res.status_code, 200)
        res = self.client.get(reverse("sports_fes:index"))     #体育祭
        self.assertEqual(res.status_code, 200)
        res = self.client.get(reverse("ya:posts_listview"))     #ya
        self.assertEqual(res.status_code, 200)
        res = self.client.get(reverse("main:mypage"))    # 管理ページ
        self.assertEqual(res.status_code, 200)

    def test_viewers(self):
        self.permission.display_home = False
        self.permission.display_introduction = False
        self.permission.display_sports_fes = False
        self.permission.save()
        res = self.client.get(reverse("main:index"))    #ホーム
        self.assertRedirects(res, reverse("main:coming_soon"), status_code=302, target_status_code=200, fetch_redirect_response=True)
        res = self.client.get(reverse("main:exhibitions", kwargs={"category": "class"}))    #展示
        self.assertRedirects(res, reverse("main:coming_soon"), status_code=302, target_status_code=200, fetch_redirect_response=True)
        res = self.client.get(reverse("sports_fes:index"))     #体育祭
        self.assertRedirects(res, reverse("sports_fes:coming_soon"), status_code=302, target_status_code=200, fetch_redirect_response=True)
        res = self.client.get("ya")     #ya
        self.assertEqual(res.status_code, 404)
        self.assertTemplateNotUsed(res, "ya/posts_listview.html")
        #公開する場合
        self.permission.display_home = True
        self.permission.display_introduction = True
        self.permission.display_sports_fes = True
        self.permission.save()
        res = self.client.get(reverse("main:index"))    #ホーム
        self.assertEqual(res.status_code, 200)
        res = self.client.get(reverse("main:exhibitions", kwargs={"category": "class"}))    #展示
        self.assertEqual(res.status_code, 200)
        res = self.client.get(reverse("sports_fes:index"))     #体育祭
        self.assertEqual(res.status_code, 200)


    def test_auth_user(self):
        self.permission.display_home = False
        self.permission.display_introduction = False
        self.permission.display_sports_fes = False
        self.permission.save()
        self.client.login(username="U0001", password="@random*0**")
        res = self.client.get(reverse("main:index"))    #ホーム
        self.assertEqual(res.status_code, 200)
        res = self.client.get(reverse("main:exhibitions", kwargs={"category": "class"}))    #展示
        self.assertRedirects(res, reverse("main:coming_soon"), status_code=302, target_status_code=200, fetch_redirect_response=True)
        res = self.client.get(reverse("sports_fes:index"))     #体育祭
        self.assertRedirects(res, reverse("sports_fes:coming_soon"), status_code=302, target_status_code=200, fetch_redirect_response=True)
        res = self.client.get(reverse("ya:posts_listview"))     #ya
        self.assertEqual(res.status_code, 404)
        self.assertTemplateNotUsed(res, "ya/posts_listview.html")

    def test_ya_user(self):
        self.permission.display_home = False
        self.permission.display_introduction = False
        self.permission.display_sports_fes = False
        self.permission.save()
        self.client.login(username="U0003", password="@random*0**")
        res = self.client.get(reverse("main:index"))    #ホーム
        self.assertEqual(res.status_code, 200)
        res = self.client.get(reverse("main:exhibitions", kwargs={"category": "class"}))    #展示
        self.assertRedirects(res, reverse("main:coming_soon"), status_code=302, target_status_code=200, fetch_redirect_response=True)
        res = self.client.get(reverse("sports_fes:index"))     #体育祭
        self.assertRedirects(res, reverse("sports_fes:coming_soon"), status_code=302, target_status_code=200, fetch_redirect_response=True)
        res = self.client.get(reverse("ya:posts_listview"))     #ya
        self.assertEqual(res.status_code, 200)


    def test_404(self):
        res = self.client.get("/path_does_not_exist")
        self.assertEqual(res.status_code, 404)
    
    def test_403_or_under_review(self):
        obj = Exhibition.objects.get(title="This is for a test")
        # 編集ページ
        self.permission.can_edit_exhibitions = True
        self.permission.save()
        res = self.client.get(reverse("main:exhibition_edit", kwargs={"pk":obj.id}))
        self.assertRedirects(res, reverse("main:under_review"), status_code=302, target_status_code=200, fetch_redirect_response=True)
        token = {"token": obj.token}    #辞書型
        res = self.client.get(
            f'{reverse("main:exhibition_edit", kwargs={"pk":obj.id})}?{urlencode(token)}'   #token付与
            )
        self.assertEqual(res.status_code, 200)

        self.permission.can_edit_exhibitions = False
        self.permission.save()
        res = self.client.get(
            f'{reverse("main:exhibition_edit", kwargs={"pk":obj.id})}?{urlencode(token)}'   #token付与
            )
        self.assertRedirects(res, reverse("main:under_review"), status_code=302, target_status_code=200, fetch_redirect_response=True)
        
        # 当日入力用
        self.permission.can_edit_attractions = True
        self.permission.save()
        res = self.client.get(reverse("main:attraction_create", kwargs={"pk":obj.id}))
        self.assertEqual(res.status_code, 403)
        res = self.client.get(
            f'{reverse("main:attraction_create", kwargs={"pk":obj.id})}?{urlencode(token)}'   #token付与
            )
        self.assertEqual(res.status_code, 200)
        self.permission.can_edit_attractions =  False
        self.permission.save()
        res = self.client.get(
            f'{reverse("main:attraction_create", kwargs={"pk":obj.id})}?{urlencode(token)}'   #token付与
            )
        self.assertEqual(res.status_code, 403)
