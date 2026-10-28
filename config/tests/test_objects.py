from colorama import init, Back, Fore, Style
init(autoreset=True) 

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
User = get_user_model()
from django.core.files import File
from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse
from urllib.parse import urlencode

from config.models import Permission
from main.models import *
from main.forms import *

import pathlib

class TestObjectsCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 後でファイルを手動削除するためのリスト
        cls.files_to_delete = []
        # 展示
        Exhibition.objects.all().delete()
        with  open("main/static/main/img/backgrounds/test.jpeg", "rb") as f:
            _ = Exhibition.objects.create(
                title = "This is for a test(9)",
                category = ExhibitionCategory.CLASS,
                grade_number = 3,
                class_number = 9,
                background = File(f, name="test.jpeg"),
            )
            try:
                cls.files_to_delete.append(_.background.path)
            except:
                pass
        # 模擬店
        FoodBooth.objects.all().delete()
        with  open("main/static/main/img/backgrounds/test.jpeg", "rb") as f:
            _ = FoodBooth.objects.create(
                name = "This is for a test(8)",
                price = 300,
                grade_number = 3,
                class_number = 9,
                background = File(f, name="test.jpeg"),
            )
            try:
                cls.files_to_delete.append(_.background.path)
            except:
                pass


    def test_exhibition1(self):
        # 画像テスト
        obj = Exhibition.objects.get(title="This is for a test(9)")
        res = self.client.get(obj.background.url)
        if settings.DEBUG:
            self.assertEqual(res.status_code, 200)

    def test_exhibition2(self):
        data = {
            "title" : "正常に返される",
            "category": ExhibitionCategory.GRADE,
            "grade_number" : 3,
            "class_number" : 8,
        }
        with  open("main/static/main/img/backgrounds/test.jpeg", "rb") as f:
            files = {
                "background" : File(f, name="test2.jpeg"),
            }
            form = ExhibitionForm(data, files)
            self.assertTrue(form.is_valid())

    def test_exhibition3(self):
        data = {
            "title" : "画像5MBオーバー",
            "category": ExhibitionCategory.GRADE,
            "grade_number" : 3,
            "class_number" : 8,
        }
        with  open("main/static/main/img/backgrounds/exceed_5mb.png", "rb") as f:
            files = {
                "background" : File(f, name="exceed_5mb.png"),
            }
            form = ExhibitionForm(data, files)
            self.assertFalse(form.is_valid())


    @classmethod
    def tearDownClass(cls): #テスト終了時に実行される
        for file in cls.files_to_delete:
            p = pathlib.Path(file)
            try:
                p.unlink()    #手動削除
            except Exception as e:
                print(Back.WHITE + Fore.RED + f"ファイル削除エラー：{e}")
        super().tearDownClass()

