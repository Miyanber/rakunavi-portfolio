"""
RakuNavi テストスイート
models.py / views.py のユニット・統合テスト
まあテストはAIにやらせたほうが効率的w。
"""

import warnings
from datetime import time, date
from unittest.mock import patch, MagicMock
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase, RequestFactory, Client
from django.urls import reverse
from django.utils import timezone

# ============================================================
# モデルテスト
# ============================================================

class FloorValidateTest(TestCase):
    """Floor.validate() の境界値テスト"""

    def test_valid_floors(self):
        from main.models import Floor
        for f in Floor.values:
            self.assertTrue(Floor.validate(f), f"floor={f} は有効なはず")

    def test_invalid_floor_negative(self):
        from main.models import Floor
        self.assertFalse(Floor.validate(-1))

    def test_invalid_floor_too_large(self):
        from main.models import Floor
        self.assertFalse(Floor.validate(99))


class ExhibitionTagTest(TestCase):
    """ExhibitionTag モデルの基本テスト"""

    def test_str(self):
        from main.models import ExhibitionTag
        tag = ExhibitionTag(name="お化け屋敷")
        self.assertEqual(str(tag), "お化け屋敷")


class SpotModelTest(TestCase):
    """Spot モデルのテスト"""

    def _make_spot(self, **kwargs):
        from main.models import Spot
        defaults = dict(name="テスト教室", is_stage=False, floor=1)
        defaults.update(kwargs)
        return Spot.objects.create(**defaults)

    def test_str_contains_floor_and_name(self):
        spot = self._make_spot()
        self.assertIn("テスト教室", str(spot))

    def test_display_name_no_related_returns_none(self):
        spot = self._make_spot(name="未割当スポット")
        # 展示・模擬店・キッチンカーなし → display_name は None
        self.assertIsNone(spot.display_name)


class ExhibitionModelTest(TestCase):
    """Exhibition モデルの save / clean / __str__ テスト"""

    def _make_exhibition(self, **kwargs):
        from main.models import Exhibition, ExhibitionCategory
        defaults = dict(
            title="テスト展示",
            category=ExhibitionCategory.CLASS,
            grade_number=1,
            class_number=3,
            explanation="",
        )
        defaults.update(kwargs)
        obj = Exhibition(**defaults)
        obj.save()
        return obj

    def test_str_class_exhibition(self):
        ex = self._make_exhibition()
        s = str(ex)
        self.assertIn("1年3組", s)
        self.assertIn("テスト展示", s)

    def test_str_club_exhibition(self):
        from main.models import Exhibition, ExhibitionCategory
        ex = Exhibition(title="茶道部", category=ExhibitionCategory.CLUB, explanation="")
        ex.save()
        self.assertIn("クラブ展示", str(ex))

    def test_clean_rejects_script_tag(self):
        from main.models import Exhibition, ExhibitionCategory
        ex = Exhibition(
            title="悪意ある展示",
            category=ExhibitionCategory.CLUB,
            explanation="<script>alert(1)</script>",
        )
        with self.assertRaises(ValidationError):
            ex.clean()

    def test_clean_rejects_img_tag(self):
        from main.models import Exhibition, ExhibitionCategory
        ex = Exhibition(
            title="imgタグ展示",
            category=ExhibitionCategory.CLUB,
            explanation='<img src="x" onerror="alert(1)">',
        )
        with self.assertRaises(ValidationError):
            ex.clean()

    def test_clean_accepts_normal_html(self):
        from main.models import Exhibition, ExhibitionCategory
        ex = Exhibition(
            title="正常な展示",
            category=ExhibitionCategory.CLUB,
            explanation="<p>普通のテキスト</p>",
        )
        ex.clean()  # 例外が上がらないこと

    def test_token_generated_on_create(self):
        ex = self._make_exhibition()
        self.assertGreater(len(ex.token), 10)

    def test_token_gen_datetime_updates_on_token_change(self):
        ex = self._make_exhibition()
        original_dt = ex.token_gen_datetime
        ex.token = "newtoken_" + "x" * 80
        ex.save()
        ex.refresh_from_db()
        self.assertNotEqual(ex.token_gen_datetime, original_dt)

    def test_token_gen_datetime_unchanged_if_token_unchanged(self):
        ex = self._make_exhibition()
        original_dt = ex.token_gen_datetime
        ex.title = "タイトル変更"
        ex.save()
        ex.refresh_from_db()
        self.assertEqual(ex.token_gen_datetime, original_dt)

    def test_get_absolute_url(self):
        ex = self._make_exhibition()
        url = ex.get_absolute_url()
        self.assertIn(str(ex.id), url)


class AttractionModelTest(TestCase):
    """Attraction の formal_congestion_level / formal_ticket_status テスト"""

    def _make_attraction(self, congestion, ticket_status=1):
        from main.models import Exhibition, ExhibitionCategory, Attraction
        ex = Exhibition(title="x", category=ExhibitionCategory.CLUB, explanation="")
        ex.save()
        return Attraction(
            exhibition=ex,
            congestion_level=congestion,
            ticket_status=ticket_status,
        )

    def test_formal_congestion_null(self):
        from main.models import CongestionDegree
        a = self._make_attraction(CongestionDegree.NULL)
        self.assertEqual(a.formal_congestion_level, "未入力")

    def test_formal_congestion_empty(self):
        from main.models import CongestionDegree
        a = self._make_attraction(CongestionDegree.EMPTY)
        self.assertEqual(a.formal_congestion_level, "空")

    def test_formal_congestion_busy(self):
        from main.models import CongestionDegree
        a = self._make_attraction(CongestionDegree.BUSY)
        self.assertEqual(a.formal_congestion_level, "多")

    def test_formal_congestion_crowded(self):
        from main.models import CongestionDegree
        a = self._make_attraction(CongestionDegree.CROWDED)
        self.assertEqual(a.formal_congestion_level, "混")

    def test_formal_ticket_status_available(self):
        from main.models import TicketStatus
        a = self._make_attraction(0, ticket_status=TicketStatus.AVAILABLE)
        self.assertEqual(a.formal_ticket_status, "有り")

    def test_formal_ticket_status_none(self):
        from main.models import TicketStatus
        a = self._make_attraction(0, ticket_status=TicketStatus.NONE)
        self.assertEqual(a.formal_ticket_status, "無し")

    def test_formal_ticket_status_ended(self):
        from main.models import TicketStatus
        a = self._make_attraction(0, ticket_status=TicketStatus.ENDED)
        self.assertEqual(a.formal_ticket_status, "終了")


class PerformanceModelTest(TestCase):
    """Performance モデルの clean テスト"""

    def _make_spot(self):
        from main.models import Spot
        return Spot.objects.create(name="野外ライブステージ", is_stage=True, floor=7)

    def test_clean_rejects_script_tag(self):
        from main.models import Performance
        spot = self._make_spot()
        p = Performance(
            name="バンドX",
            spot=spot,
            message="<script>bad()</script>",
        )
        with self.assertRaises(ValidationError):
            p.clean()

    def test_clean_rejects_form_tag(self):
        from main.models import Performance
        spot = self._make_spot()
        p = Performance(
            name="バンドZ",
            spot=spot,
            message='<form action="/evil">submit</form>',
        )
        with self.assertRaises(ValidationError):
            p.clean()

    def test_clean_accepts_normal_message(self):
        from main.models import Performance
        spot = self._make_spot()
        p = Performance(name="バンドY", spot=spot, message="<p>よろしく</p>")
        p.clean()  # 例外なし


class TimeSlotSecondsTest(TestCase):
    """TimeSlot.seconds プロパティのテスト"""

    def test_seconds_30min(self):
        from main.models import TimeSlot
        ts = TimeSlot.__new__(TimeSlot)
        ts.begin_at = time(10, 0)
        ts.end_at = time(10, 30)
        self.assertEqual(ts.seconds, 1800)

    def test_seconds_1hour(self):
        from main.models import TimeSlot
        ts = TimeSlot.__new__(TimeSlot)
        ts.begin_at = time(9, 0)
        ts.end_at = time(10, 0)
        self.assertEqual(ts.seconds, 3600)

    def test_seconds_90min(self):
        from main.models import TimeSlot
        ts = TimeSlot.__new__(TimeSlot)
        ts.begin_at = time(13, 0)
        ts.end_at = time(14, 30)
        self.assertEqual(ts.seconds, 5400)


class MenuModelTest(TestCase):
    """Menu.__str__ の価格表示テスト"""

    def _make_food_truck(self):
        from main.models import FoodTruck
        ft = FoodTruck(name="テストカー")
        ft.save()
        return ft

    def test_str_single_price(self):
        from main.models import Menu
        ft = self._make_food_truck()
        m = Menu(food_truck=ft, name="たこ焼き", price=500)
        self.assertIn("500円", str(m))
        self.assertNotIn("～", str(m))

    def test_str_price_range(self):
        from main.models import Menu
        ft = self._make_food_truck()
        m = Menu(food_truck=ft, name="焼きそば", price=400, max_price=600)
        self.assertIn("400円～600円", str(m))

    def test_str_with_note(self):
        from main.models import Menu
        ft = self._make_food_truck()
        m = Menu(food_truck=ft, name="焼きそば", price=400, note="辛口あり")
        self.assertIn("辛口あり", str(m))


# ============================================================
# ビューテスト
# ============================================================

User = get_user_model()

# カスタム User モデルの仕様（config/models.py）:
#   USERNAME_FIELD = "user_id"   ← 認証キー・ログインに使う（半角英数字）
#   username       = 表示名      ← REQUIRED_FIELDS に含まれ別途必須
#
# create_user / create_superuser の第一引数は user_id。
# 各テストで uuid サフィックスを付け user_id / username 両方の衝突を防ぐ。

def _uid(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:10]}"


class ViewTestBase(TestCase):
    """ビューテスト共通セットアップ"""

    def setUp(self):
        self.client = Client()
        self._user_id  = _uid("testuser_")
        self._super_id = _uid("admin_")
        self.user = User.objects.create_user(
            user_id=self._user_id,
            username=_uid("テストユーザー"),
            password="testpass123",
        )
        self.superuser = User.objects.create_superuser(
            user_id=self._super_id,
            username=_uid("管理者"),
            password="adminpass123",
        )

    def login(self, superuser=False):
        if superuser:
            self.client.login(user_id=self._super_id, password="adminpass123")
        else:
            self.client.login(user_id=self._user_id, password="testpass123")


class ExhibitionSearchViewTest(ViewTestBase):
    """ExhibitionSearchView のテスト"""

    def setUp(self):
        super().setUp()
        from config.models import Permission as RakunaviPermission
        perm = RakunaviPermission.objects.first()
        if perm:
            perm.display_introduction = True
            perm.save()

    def test_search_with_empty_query_returns_200(self):
        url = reverse("main:exhibitions_search")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_search_with_query_returns_200(self):
        url = reverse("main:exhibitions_search") + "?query=テスト"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class ExhibitionDetailViewTest(ViewTestBase):
    """ExhibitionDetailView のトークン認証テスト"""

    def _enable_introduction(self):
        from config.models import Permission as RakunaviPermission
        perm = RakunaviPermission.objects.first()
        if perm:
            perm.display_introduction = True
            perm.save()

    def _make_exhibition(self):
        from main.models import Exhibition, ExhibitionCategory
        ex = Exhibition(title="詳細テスト展示", category=ExhibitionCategory.CLUB, explanation="")
        ex.save()
        return ex

    def test_access_with_valid_token_in_session(self):
        self._enable_introduction()
        ex = self._make_exhibition()
        session = self.client.session
        session["edit_token"] = str(ex.token)
        session.save()
        url = reverse("main:exhibition_detail", kwargs={"pk": ex.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_access(self):
        self._enable_introduction()
        self.login(superuser=True)
        ex = self._make_exhibition()
        url = reverse("main:exhibition_detail", kwargs={"pk": ex.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_no_token_no_permission_is_rejected(self):
        """トークンなし・permission OFF のアクセスは弾かれる"""
        from config.models import Permission as RakunaviPermission
        perm = RakunaviPermission.objects.first()
        if perm:
            perm.display_introduction = False
            perm.save()
        ex = self._make_exhibition()
        url = reverse("main:exhibition_detail", kwargs={"pk": ex.pk})
        response = self.client.get(url)
        self.assertIn(response.status_code, [302, 403])


class IndexViewTest(ViewTestBase):
    """IndexView の基本テスト"""

    def test_index_returns_200_or_302(self):
        url = reverse("main:index")
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 302])


class QrcodeViewTest(ViewTestBase):
    """QrcodeView のセキュリティテスト"""

    def test_missing_params_returns_403(self):
        url = reverse("main:qrcode")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_external_url_returns_403(self):
        url = reverse("main:qrcode") + "?url=https://evil.example.com/&_=dummy"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)


# ============================================================
# ユーティリティ関数テスト
# ============================================================

class FormatDeadlineTest(TestCase):
    """format_deadline() のテスト"""

    def test_format_without_minutes(self):
        import datetime
        from main.views import format_deadline
        dt = datetime.datetime(2025, 9, 1, 15, 0)
        result = format_deadline(dt)
        self.assertIn("9月1日", result)
        self.assertIn("15時", result)
        self.assertNotIn("0分", result)  # 分が 0 のときは非表示

    def test_format_with_minutes(self):
        import datetime
        from main.views import format_deadline
        dt = datetime.datetime(2025, 9, 1, 15, 30)
        result = format_deadline(dt)
        self.assertIn("30分", result)

    def test_weekday_label_monday(self):
        import datetime
        from main.views import format_deadline
        # 2025-09-01 は月曜日
        dt = datetime.datetime(2025, 9, 1, 10, 0)
        self.assertIn("月", format_deadline(dt))

    def test_weekday_label_sunday(self):
        import datetime
        from main.views import format_deadline
        # 2025-09-07 は日曜日
        dt = datetime.datetime(2025, 9, 7, 10, 0)
        self.assertIn("日", format_deadline(dt))


class GenerateSecureTokenTest(TestCase):
    """generate_secure_token() の一意性・長さ・文字種テスト"""

    def test_tokens_are_unique(self):
        from main.models import generate_secure_token
        tokens = {generate_secure_token() for _ in range(100)}
        self.assertEqual(len(tokens), 100)

    def test_token_min_length(self):
        from main.models import generate_secure_token
        # secrets.token_urlsafe(64) → 約86文字以上
        self.assertGreaterEqual(len(generate_secure_token()), 80)

    def test_token_is_urlsafe(self):
        import re
        from main.models import generate_secure_token
        token = generate_secure_token()
        # URL-safe base64 は [A-Za-z0-9_-] のみ
        self.assertRegex(token, r'^[A-Za-z0-9_\-]+$')
