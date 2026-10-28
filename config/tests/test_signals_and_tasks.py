"""
RakuNavi テストスイート（追加）
signals / tasks のユニットテスト
Claude様様。
"""

import warnings
from datetime import timedelta
from unittest.mock import patch, MagicMock, call

from django.test import TestCase
from django.utils import timezone


# ============================================================
# signals テスト
# sync_floor_tags: Exhibition.spots の M2M 変更時に
#                  階タグを自動同期するシグナルハンドラ
# ============================================================

class SyncFloorTagsSignalTest(TestCase):
    """
    sync_floor_tags シグナルのテスト

    Exhibition に Spot を add / remove / clear したとき、
    対応する階タグが正しく付与・削除されるかを検証する。
    """

    def _make_spot(self, name, floor):
        from main.models import Spot
        return Spot.objects.create(name=name, is_stage=False, floor=floor)

    def _make_exhibition(self):
        from main.models import Exhibition, ExhibitionCategory
        ex = Exhibition(title="シグナルテスト展示", category=ExhibitionCategory.CLUB, explanation="")
        ex.save()
        return ex

    def _floor_tag_names(self, exhibition):
        """展示に付与されているタグ名の集合を返す"""
        return set(exhibition.tags.values_list("name", flat=True))

    # ------------------------------------------------------------------
    # post_add
    # ------------------------------------------------------------------

    def test_post_add_single_spot_adds_floor_tag(self):
        """Spot を 1 つ追加すると、その階のタグが付く"""
        from main.models import Floor
        ex = self._make_exhibition()
        spot = self._make_spot("本館1階の教室", floor=Floor.FIRST)

        ex.spots.add(spot)

        self.assertIn(Floor(Floor.FIRST).label, self._floor_tag_names(ex))

    def test_post_add_multiple_spots_same_floor_adds_single_tag(self):
        """同じ階の Spot を複数追加しても階タグは 1 つだけ付く"""
        from main.models import Floor
        ex = self._make_exhibition()
        spot1 = self._make_spot("本館2階A", floor=Floor.SECOND)
        spot2 = self._make_spot("本館2階B", floor=Floor.SECOND)

        ex.spots.add(spot1, spot2)

        tags = self._floor_tag_names(ex)
        floor_label = Floor(Floor.SECOND).label
        self.assertIn(floor_label, tags)
        # 同名タグが 2 つ存在しないこと（タグ名の重複なし）
        self.assertEqual(
            ex.tags.filter(name=floor_label).count(), 1
        )

    def test_post_add_spots_on_different_floors(self):
        """異なる階の Spot を追加すると両方の階タグが付く"""
        from main.models import Floor
        ex = self._make_exhibition()
        spot1 = self._make_spot("本館1階の部屋", floor=Floor.FIRST)
        spot2 = self._make_spot("本館3階の部屋", floor=Floor.THIRD)

        ex.spots.add(spot1, spot2)

        tags = self._floor_tag_names(ex)
        self.assertIn(Floor(Floor.FIRST).label, tags)
        self.assertIn(Floor(Floor.THIRD).label, tags)

    def test_post_add_does_not_remove_non_floor_tags(self):
        """Spot 追加時に、階タグ以外の既存タグは消えない"""
        from main.models import Floor, ExhibitionTag
        ex = self._make_exhibition()
        custom_tag, _ = ExhibitionTag.objects.get_or_create(name="おすすめ")
        ex.tags.add(custom_tag)

        spot = self._make_spot("本館2階の教室", floor=Floor.SECOND)
        ex.spots.add(spot)

        self.assertIn("おすすめ", self._floor_tag_names(ex))

    # ------------------------------------------------------------------
    # post_remove
    # ------------------------------------------------------------------

    def test_post_remove_spot_removes_its_floor_tag(self):
        """Spot を remove すると、その階タグが消える"""
        from main.models import Floor
        ex = self._make_exhibition()
        spot = self._make_spot("本館4階の教室", floor=Floor.FOURTH)
        ex.spots.add(spot)

        ex.spots.remove(spot)

        self.assertNotIn(Floor(Floor.FOURTH).label, self._floor_tag_names(ex))

    def test_post_remove_one_spot_keeps_tag_if_another_spot_same_floor_exists(self):
        """同じ階に別の Spot が残っていれば、階タグは保持される"""
        from main.models import Floor
        ex = self._make_exhibition()
        spot1 = self._make_spot("本館2階A教室", floor=Floor.SECOND)
        spot2 = self._make_spot("本館2階B教室", floor=Floor.SECOND)
        ex.spots.add(spot1, spot2)

        ex.spots.remove(spot1)  # spot2 はまだある

        self.assertIn(Floor(Floor.SECOND).label, self._floor_tag_names(ex))

    # ------------------------------------------------------------------
    # post_clear
    # ------------------------------------------------------------------

    def test_post_clear_removes_all_floor_tags(self):
        """spots.clear() すると全ての階タグが消える"""
        from main.models import Floor
        ex = self._make_exhibition()
        spot1 = self._make_spot("本館1階の部屋X", floor=Floor.FIRST)
        spot2 = self._make_spot("本館3階の部屋X", floor=Floor.THIRD)
        ex.spots.add(spot1, spot2)

        ex.spots.clear()

        tags = self._floor_tag_names(ex)
        floor_labels = {Floor(f).label for f, _ in Floor.choices}
        self.assertTrue(tags.isdisjoint(floor_labels),
                        f"階タグが残っている: {tags & floor_labels}")

    def test_post_clear_keeps_non_floor_tags(self):
        """spots.clear() しても、階タグ以外のタグは残る"""
        from main.models import Floor, ExhibitionTag
        ex = self._make_exhibition()
        custom_tag, _ = ExhibitionTag.objects.get_or_create(name="体験型")
        ex.tags.add(custom_tag)

        spot = self._make_spot("本館1階の部屋Y", floor=Floor.FIRST)
        ex.spots.add(spot)
        ex.spots.clear()

        self.assertIn("体験型", self._floor_tag_names(ex))

    # ------------------------------------------------------------------
    # 冪等性
    # ------------------------------------------------------------------

    def test_idempotent_readd_same_spot(self):
        """同じ Spot を 2 回 add しても状態は変わらない"""
        from main.models import Floor
        ex = self._make_exhibition()
        spot = self._make_spot("本館1階の部屋Z", floor=Floor.FIRST)

        ex.spots.add(spot)
        tag_count_first = ex.tags.count()

        ex.spots.add(spot)  # 重複 add
        tag_count_second = ex.tags.count()

        self.assertEqual(tag_count_first, tag_count_second)


# ============================================================
# tasks テスト
# auto_change_permissions: 期限チェックと Permission フィールド更新
# ============================================================

class AutoChangePermissionsTest(TestCase):
    """
    auto_change_permissions() のテスト

    Permission オブジェクトの各フラグが、期限到来時に正しく
    変更されるかを検証する。スケジューラは起動しない。
    """

    def _make_permission(self, **kwargs):
        """テスト用の Permission レコードを作る（既存があれば使う）"""
        from config.models import Permission
        perm = Permission.objects.first()
        if perm is None:
            # Permission は singleton (id=1, editable=False) なので直接生成は難しい。
            # テスト用にデフォルト値を設定してから上書きする。
            perm = Permission(id=1)
        # 安全なデフォルト: 全フラグ OFF、全期限を未来に設定
        future = timezone.now() + timedelta(days=365)
        perm.display_home = False
        perm.display_introduction = False
        perm.beta_status = True
        perm.can_edit_exhibitions = True
        perm.can_edit_attractions = True
        perm.can_edit_performances = True
        perm.can_edit_foodbooth = True
        perm.exhibitions_editing_deadline = future
        perm.exhibitions_editing_deadline_scheduled = False
        perm.food_booths_editing_deadline = future
        perm.food_booths_editing_deadline_scheduled = False
        perm.performances_editing_deadline = future
        perm.performances_editing_deadline_scheduled = False
        perm.publishing_datetime = future
        perm.publishing_datetime_scheduled = False
        perm.allow_attraction_create_datetime = future
        perm.allow_attraction_create_datetime_scheduled = False
        perm.map_key = "testkey"
        for k, v in kwargs.items():
            setattr(perm, k, v)
        perm.save()
        return perm

    def _run(self):
        """auto_change_permissions() を直接呼び出す"""
        from config.tasks import auto_change_permissions
        auto_change_permissions()

    # ------------------------------------------------------------------
    # 展示の編集期限
    # ------------------------------------------------------------------

    def test_exhibition_deadline_passed_disables_editing(self):
        """展示編集期限が過去 + scheduled=True → 編集フラグが False になる"""
        past = timezone.now() - timedelta(minutes=5)
        self._make_permission(
            exhibitions_editing_deadline=past,
            exhibitions_editing_deadline_scheduled=True,
            can_edit_exhibitions=True,
            can_edit_attractions=True,
        )

        self._run()

        from config.models import Permission
        perm = Permission.objects.first()
        self.assertFalse(perm.can_edit_exhibitions)
        self.assertFalse(perm.can_edit_attractions)
        self.assertFalse(perm.exhibitions_editing_deadline_scheduled)

    def test_exhibition_deadline_future_does_not_change(self):
        """展示編集期限が未来 → フラグは変わらない"""
        future = timezone.now() + timedelta(hours=1)
        self._make_permission(
            exhibitions_editing_deadline=future,
            exhibitions_editing_deadline_scheduled=True,
            can_edit_exhibitions=True,
        )

        self._run()

        from config.models import Permission
        perm = Permission.objects.first()
        self.assertTrue(perm.can_edit_exhibitions)

    def test_exhibition_deadline_not_scheduled_does_not_change(self):
        """scheduled=False なら期限が過去でも変更されない"""
        past = timezone.now() - timedelta(minutes=5)
        self._make_permission(
            exhibitions_editing_deadline=past,
            exhibitions_editing_deadline_scheduled=False,
            can_edit_exhibitions=True,
        )

        self._run()

        from config.models import Permission
        perm = Permission.objects.first()
        self.assertTrue(perm.can_edit_exhibitions)

    # ------------------------------------------------------------------
    # 模擬店の編集期限
    # ------------------------------------------------------------------

    def test_food_booth_deadline_passed_disables_editing(self):
        past = timezone.now() - timedelta(minutes=5)
        self._make_permission(
            food_booths_editing_deadline=past,
            food_booths_editing_deadline_scheduled=True,
            can_edit_foodbooth=True,
        )

        self._run()

        from config.models import Permission
        perm = Permission.objects.first()
        self.assertFalse(perm.can_edit_foodbooth)
        self.assertFalse(perm.food_booths_editing_deadline_scheduled)

    # ------------------------------------------------------------------
    # ライブの編集期限
    # ------------------------------------------------------------------

    def test_performance_deadline_passed_disables_editing(self):
        past = timezone.now() - timedelta(minutes=5)
        self._make_permission(
            performances_editing_deadline=past,
            performances_editing_deadline_scheduled=True,
            can_edit_performances=True,
        )

        self._run()

        from config.models import Permission
        perm = Permission.objects.first()
        self.assertFalse(perm.can_edit_performances)
        self.assertFalse(perm.performances_editing_deadline_scheduled)

    # ------------------------------------------------------------------
    # 自動公開
    # ------------------------------------------------------------------

    def test_publishing_datetime_passed_enables_display(self):
        """公開日時が過去 + scheduled=True → display_home / display_introduction が True に"""
        past = timezone.now() - timedelta(minutes=1)
        self._make_permission(
            publishing_datetime=past,
            publishing_datetime_scheduled=True,
            display_home=False,
            display_introduction=False,
            beta_status=True,
        )

        self._run()

        from config.models import Permission
        perm = Permission.objects.first()
        self.assertTrue(perm.display_home)
        self.assertTrue(perm.display_introduction)
        self.assertFalse(perm.beta_status)
        self.assertFalse(perm.publishing_datetime_scheduled)

    def test_publishing_datetime_future_no_change(self):
        future = timezone.now() + timedelta(hours=1)
        self._make_permission(
            publishing_datetime=future,
            publishing_datetime_scheduled=True,
            display_home=False,
        )

        self._run()

        from config.models import Permission
        perm = Permission.objects.first()
        self.assertFalse(perm.display_home)

    # ------------------------------------------------------------------
    # 当日編集の解放
    # ------------------------------------------------------------------

    def test_attraction_create_datetime_passed_enables_attraction_editing(self):
        past = timezone.now() - timedelta(minutes=1)
        self._make_permission(
            allow_attraction_create_datetime=past,
            allow_attraction_create_datetime_scheduled=True,
            can_edit_attractions=False,
        )

        self._run()

        from config.models import Permission
        perm = Permission.objects.first()
        self.assertTrue(perm.can_edit_attractions)
        self.assertFalse(perm.allow_attraction_create_datetime_scheduled)

    # ------------------------------------------------------------------
    # 複数フラグの同時変更
    # ------------------------------------------------------------------

    def test_multiple_deadlines_passed_all_updated_at_once(self):
        """複数の期限が同時に過去なら、全てのフラグが一度の save() で更新される"""
        past = timezone.now() - timedelta(minutes=5)
        self._make_permission(
            exhibitions_editing_deadline=past,
            exhibitions_editing_deadline_scheduled=True,
            food_booths_editing_deadline=past,
            food_booths_editing_deadline_scheduled=True,
            performances_editing_deadline=past,
            performances_editing_deadline_scheduled=True,
            can_edit_exhibitions=True,
            can_edit_foodbooth=True,
            can_edit_performances=True,
        )

        self._run()

        from config.models import Permission
        perm = Permission.objects.first()
        self.assertFalse(perm.can_edit_exhibitions)
        self.assertFalse(perm.can_edit_foodbooth)
        self.assertFalse(perm.can_edit_performances)

    def test_no_deadline_passed_save_not_called(self):
        """期限が全て未来のとき、Permission.save() は呼ばれない（DB 書き込みなし）"""
        future = timezone.now() + timedelta(hours=1)
        perm = self._make_permission(
            exhibitions_editing_deadline=future,
            exhibitions_editing_deadline_scheduled=True,
            food_booths_editing_deadline=future,
            food_booths_editing_deadline_scheduled=True,
            performances_editing_deadline=future,
            performances_editing_deadline_scheduled=True,
            publishing_datetime=future,
            publishing_datetime_scheduled=True,
            allow_attraction_create_datetime=future,
            allow_attraction_create_datetime_scheduled=True,
        )

        from config.models import Permission
        with patch.object(Permission, 'save', wraps=perm.save) as mock_save:
            self._run()
            mock_save.assert_not_called()


# ============================================================
# tasks.start() テスト
# スケジューラが正しいジョブ設定で起動するかをモックで検証
# ============================================================

class TasksStartTest(TestCase):
    """
    tasks.start() のテスト

    実際のスケジューラは起動せず、BackgroundScheduler をモックして
    ジョブが正しく登録されているかを確認する。
    """

    @patch("config.tasks.BackgroundScheduler")
    def test_start_registers_two_jobs(self, MockScheduler):
        """start() が auto_change_permissions と backup_db の 2 ジョブを登録する"""
        from config.tasks import start
        mock_instance = MockScheduler.return_value

        start()

        self.assertEqual(mock_instance.add_job.call_count, 2)
        mock_instance.start.assert_called_once()

    @patch("config.tasks.BackgroundScheduler")
    def test_auto_change_permissions_job_is_interval(self, MockScheduler):
        """auto_change_permissions ジョブが interval トリガーで登録される"""
        from config.tasks import start
        mock_instance = MockScheduler.return_value

        start()

        calls = mock_instance.add_job.call_args_list
        # 1 つ目のジョブが interval
        first_call_args = calls[0]
        self.assertEqual(first_call_args[0][1], "interval")  # trigger
        self.assertEqual(first_call_args[1].get("id"), "auto_change_permissions")
        self.assertEqual(first_call_args[1].get("minutes"), 1)

    @patch("config.tasks.BackgroundScheduler")
    def test_backup_db_job_is_cron(self, MockScheduler):
        """backup_db ジョブが cron トリガーで登録される"""
        from config.tasks import start
        mock_instance = MockScheduler.return_value

        start()

        calls = mock_instance.add_job.call_args_list
        # 2 つ目のジョブが cron
        second_call_args = calls[1]
        self.assertEqual(second_call_args[0][1], "cron")
        self.assertEqual(second_call_args[1].get("id"), "backup_db")
        self.assertEqual(second_call_args[1].get("hour"), 2)

    @patch("config.tasks.BackgroundScheduler")
    def test_all_jobs_have_replace_existing_and_coalesce(self, MockScheduler):
        """全ジョブに replace_existing=True, coalesce=True が設定されている"""
        from config.tasks import start
        mock_instance = MockScheduler.return_value

        start()

        for job_call in mock_instance.add_job.call_args_list:
            kwargs = job_call[1]
            self.assertTrue(kwargs.get("replace_existing"),
                            f"replace_existing が True でない: {kwargs}")
            self.assertTrue(kwargs.get("coalesce"),
                            f"coalesce が True でない: {kwargs}")
