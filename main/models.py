from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToCover
from typing import Iterable
from django.db import models
from django.db.models import Q
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

from config.models import get_random_name
from main.convert import convert_to_webp, validate_image_size

from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import secrets


# ImageFieldの画像のアップロード先を定義
# Supabaseでは画像名で日本語不可だった（過去形）
def image_upload_path(instance, filename):
    return f"images/{get_random_name()}{Path(filename).suffix}"

def performance_image_upload_path(instance, filename):
    return f"images/performance/{get_random_name()}{Path(filename).suffix}"

def performance_member_image_upload_path(instance, filename):
    return f"images/performance/member/{get_random_name()}{Path(filename).suffix}"

def exhibition_image_upload_path(instance, filename):
    return f"images/exhibition/{get_random_name()}{Path(filename).suffix}"

def food_booth_image_upload_path(instance, filename):
    return f"images/foodbooth/{get_random_name()}{Path(filename).suffix}"

def food_truck_image_upload_path(instance, filename):
    return f"images/foodtruck/{get_random_name()}{Path(filename).suffix}"

def general_image_upload_path(instance, filename):
    return f"images/others/{get_random_name()}{Path(filename).suffix}"

def video_file_upload_path(instance, filename):
    return f"videos/exhibition/{instance}{Path(filename).suffix}"

def generate_secure_token():
    # 約86文字 (512ビット分のランダム性)、ブルートフォース耐性向上
    return secrets.token_urlsafe(64)

def max_file_size(value):
    limit = 1000*1000*40 #Biteで計算、40MB
    if value.size>limit:
        raise ValidationError('Your file is too large. It should not exceed 40MB.')


# 展示の種類 Enum
class ExhibitionCategory(models.TextChoices):
    CLASS = "class", "クラス展示"
    CLUB = "club", "クラブ展示"
    GRADE = "grade", "学年展示"
    FACILITY = "facility", "施設・その他"


# 混雑度合 Enum
class CongestionDegree(models.IntegerChoices):
    NULL = -1 ,'未入力'
    EMPTY = 0 ,'空いている'
    NORMAL = 1 ,'普通'
    BUSY = 2 ,'混んでいる'
    CROWDED = 3 ,'非常に混雑'


class Floor(models.IntegerChoices):
    B_FIRST = 0, '地下1階'
    FIRST = 1, '本館1階'
    SECOND = 2, '本館2階'
    THIRD = 3, '本館3階'
    FOURTH = 4, '本館4階'
    N_FIRST = 5, '北館1階'
    N_SECOND = 6, '北館2階'
    YOUTH_SQUARE = 7, '青春の広場'

    @staticmethod
    def validate(floor: int) -> bool:
        return not (floor < Floor.B_FIRST or floor > Floor.YOUTH_SQUARE)


class ExhibitionTag(models.Model):
    """展示に他対他で結びつけるタグ
    """
    name = models.CharField("タグの名前", max_length=20)

    def __str__(self):
        return f'{self.name}'
    
    class Meta:
        verbose_name = "🇪タグ"
        verbose_name_plural = "🇪タグ"


class SortableModel(models.Model):
    """順番を管理するモデル用の抽象クラス
    """    
    order = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ["order"]


class TimeSlot(models.Model):
    """開始時刻・終了時刻・開催日を持つ時間枠モデル
    """
    date = models.ForeignKey("config.FestivalDate", verbose_name="開催日", on_delete=models.CASCADE, related_name="events")     #循環import阻止
    begin_at = models.TimeField("開始時刻")
    end_at = models.TimeField("終了時刻")
    
    @property
    def seconds(self) -> int:
        return (datetime.combine(datetime.today(), self.end_at) - datetime.combine(datetime.today(), self.begin_at)).seconds

    def __str__(self):
            return f"{self.date} {self.begin_at.strftime('%H:%M')} ～ {self.end_at.strftime('%H:%M')}"

    class Meta:
        verbose_name = "🇪時間枠"
        verbose_name_plural = "🇪時間枠"
        ordering = ['date', 'begin_at', ]
        

class Allergens(models.Model):
    """模擬店に他対他で結びつける、アレルゲン
    """
    name = models.CharField("アレルゲン名", max_length=20)

    def __str__(self):
        return f'{self.name}'
    
    class Meta:
        verbose_name = "🇫アレルゲン"
        verbose_name_plural = "🇫アレルゲン"


# 場所モデル：地図上の位置情報を格納
class Spot(models.Model):
    name = models.CharField(
        "名称", 
        help_text="HR教室名の場合、数字は半角で「高校2年3組」という書き方に統一して下さい。", 
        max_length=50, 
        unique=True
    )
    is_stage = models.BooleanField("ライブステージかどうか")
    floor = models.SmallIntegerField("階", choices=Floor.choices)
    start_x = models.FloatField("start_x", default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    start_y = models.FloatField("start_y", default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    width = models.FloatField("width", default=7, validators=[MinValueValidator(0), MaxValueValidator(100)])
    height = models.FloatField("height", default=14, validators=[MinValueValidator(0), MaxValueValidator(100)])

    @property
    def display_name(self):
        try:
            exhibitions = self.exhibitions
            return exhibitions.first()
        except Exhibition.DoesNotExist:
            pass

        try:
            food_booth = self.food_booth
            return food_booth.name
        except FoodBooth.DoesNotExist:
            pass

        try:
            food_truck = self.food_truck
            return food_truck.name
        except FoodTruck.DoesNotExist:
            pass

        return self.name

    def __str__(self) -> str:
        return f'{Floor(self.floor).label} {self.name}'


    class Meta:
        verbose_name = "📍場所"
        verbose_name_plural = "📍場所"
        ordering = ['floor', 'name', ]
        permissions = [
            ("can_view_map", "Can view the map page"),
        ]


class Exhibition(models.Model):
    token = models.CharField("トークン", max_length=100, unique=True, default=generate_secure_token)
    token_gen_datetime = models.DateTimeField("トークン生成日時", default=timezone.now)
    title = models.CharField("展示タイトル", max_length=50)
    category = models.CharField("展示の種類", max_length=25, choices=ExhibitionCategory.choices)
    overview = models.CharField(
        "概要", 
        help_text='展示の概要です。一覧ページに表示されます。Ex.) 「ジェットコースター」,「対戦型縁日 腕相撲やってます！」etc. 最大文字数は50字です。', 
        max_length=50,
        blank=True
    )
    tags = models.ManyToManyField(ExhibitionTag, related_name="exhibitions", blank=True, verbose_name="タグ")
    explanation = CKEditor5Field(
        "詳細説明", 
        help_text='展示の紹介文です。詳細ページに表示されます。200~300字程度が理想です。展示のテーマを明確にし、\
            展示の見どころが来場者に伝わるように、注目してほしい点や展示の特長を記載する等して工夫して下さい。', 
        blank=True,
        config_name='extends'   #settingsのextends設定を使用
    )
    thumbnail = models.ImageField(
        "サムネイル画像", 
        upload_to=exhibition_image_upload_path, 
        help_text='アイコン画像として、一覧ページと詳細ページの両方に表示されます。縦横比は1:1が推奨です。設定しない場合は校章アイコン（サンプル）が表示されます。\
            ファイル形式はWebp, PNG, JPG(JPEG)が推奨です。', 
        blank=True, 
        null=True,
        validators=[validate_image_size],
    )
    thumbnail_avif = ImageSpecField(
        source='thumbnail',
        format='avif',
        options={'quality': 60},
        # processors=[ResizeToCover(800, 800)],
    )
    background = models.ImageField(
        "詳細画像", 
        help_text='背景画像として、一覧ページと詳細ページの両方に表示されます。縦横比は4:3が推奨です。設定しない場合は校章アイコン（サンプル）が表示されます。\
            ファイル形式はWebp, PNG, JPG(JPEG)が推奨です。', 
        upload_to=exhibition_image_upload_path, 
        blank=True, 
        null=True,
        validators=[validate_image_size],
    )
    background_avif= ImageSpecField(
        source='background',
        format='avif',
        options={'quality': 60},
    )
    spots = models.ManyToManyField(Spot, verbose_name="場所", related_name="exhibitions", blank=True)
    video_youtube = models.TextField("動画用埋め込みコード", blank=True)
    video_file = models.FileField(
        "動画ファイル", upload_to=video_file_upload_path, help_text="CM動画ファイル", blank=True, null=True,
        validators=[FileExtensionValidator(allowed_extensions=['mp4', ]),max_file_size]
        )
    
    grade_number = models.IntegerField("学年", validators=[MinValueValidator(1), MaxValueValidator(3)], blank=True, null=True)
    class_number = models.IntegerField("クラス", validators=[MinValueValidator(1), MaxValueValidator(10)], blank=True, null=True)
    updated_at = models.DateTimeField("最終更新", auto_now=True)

    def __str__(self):
        if self.category:
            if self.category == ExhibitionCategory.CLASS and self.grade_number and self.class_number:
                return f'{self.grade_number}年{self.class_number}組{ExhibitionCategory(self.category).label} {self.title}'
            return f'{ExhibitionCategory(self.category).label} {self.title}'
        return f'{self.title}'
    
    def clean(self):
        soup = BeautifulSoup(self.explanation, "html.parser")
        # 不正なタグの検出
        if soup.find("script") or soup.find("link") or soup.find("plaintext") \
            or soup.find("xmp") or soup.find("meta") or soup.find("body") or soup.find("img") or soup.find("form"):
            raise ValidationError({"explanation": "説明に不正なタグ・要素が含まれています。"})

    def save(self, *args, **kwargs):
        self.full_clean()  # バリデーション実行
        if self.pk:
            old = Exhibition.objects.filter(pk=self.pk).values("token").first()
            if old and old["token"] != self.token:
                # token が変更された場合のみgendatetimeを更新
                self.token_gen_datetime = timezone.now()

        # super().save(*args, **kwargs) #これなくても安全？
        # 画像をWebPに変換する
        if self.thumbnail and not self.thumbnail.name.endswith(".webp"):
            self.thumbnail = convert_to_webp(self.thumbnail, width=500)
        if self.background and not self.background.name.endswith(".webp"):
            self.background = convert_to_webp(self.background, width=1200)
        super().save(*args, **kwargs)  # 圧縮後に保存
    
    # サイトマップに必要
    def get_absolute_url(self):
        return reverse("main:exhibition_detail", args=[str(self.id)])

    class Meta:
        verbose_name = "🇪展示🚩"
        verbose_name_plural = "🇪展示🚩"
        permissions = [
            ("can_review_exhibition", "展示の審査権限"),
            ("can_download_exhibition_review", "展示の差し戻し報告PDFをダウンロードする権限"),
        ]

class TicketStatus(models.IntegerChoices):

    UNDEFINED = 0, "未入力"
    NONE = 1, "無し"
    FEW = 2, "残りわずか"
    AVAILABLE = 3, "有り"
    ENDED = 4, "終了"

class Attraction(models.Model):
    """
    混雑度・待ち時間表示用モデル
    """
    exhibition = models.ForeignKey(Exhibition, verbose_name="展示", on_delete=models.CASCADE, related_name="attractions")
    time_required = models.SmallIntegerField("所要時間 (分)", null=True, blank=True, help_text="展示を体験・観覧するのに必要な時間です。")
    congestion_level = models.SmallIntegerField("混雑度", choices=CongestionDegree.choices, default=CongestionDegree.NULL)
    wait_time = models.SmallIntegerField("待ち時間 (分)", null=True, blank=True, help_text="展示に入るまでの待ち時間です。")
    announcement = models.CharField("お知らせ", max_length=100, blank=True)
    created_at = models.DateTimeField("更新時間", auto_now=True)

    # 追加：整理券配布状況
    ticket_status = models.SmallIntegerField(
        "整理券配布", 
        choices=TicketStatus.choices, 
        default=TicketStatus.NONE
    )

    @property
    def formal_ticket_status(self) -> str:
        """表示用の整理券ステータスを返す"""
        # choicesのラベル（"無", "有", "終"）をそのまま返す場合
        return TicketStatus(self.ticket_status).label

    @property
    def formal_congestion_level(self) -> str:
        if self.congestion_level == CongestionDegree.NULL:
            return "未入力"
        elif self.congestion_level == CongestionDegree.EMPTY:
            return "空"
        elif self.congestion_level == CongestionDegree.NORMAL:
            return "普通"
        elif self.congestion_level == CongestionDegree.BUSY:
            return "多"
        elif self.congestion_level == CongestionDegree.CROWDED:
            return "混"
        return CongestionDegree(self.congestion_level).label

    def __str__(self):
        return f"{self.exhibition.title} {self.created_at}"


    class Meta:
        verbose_name = "🇦展示用当日設定🚩"
        verbose_name_plural = "🇦展示用当日設定🚩"


# 演奏モデル(出場者グループ)
class Performance(models.Model):
    id = models.BigAutoField("ID", unique=True, primary_key=True)
    token = models.CharField("トークン", max_length=100, unique=True, default=generate_secure_token)
    token_gen_datetime = models.DateTimeField("トークン生成日時", default=timezone.now)
    name = models.CharField(
        "グループ名", 
        help_text='絵文字などは含まないで下さい。', 
        max_length=50,
    )
    genre = models.CharField(
        "種類/ジャンル", 
        help_text='Ex.) JPopバンド, お笑い, Jazzバンド, ダンス etc.',
        max_length=50,
        null=True,
    )
    message = CKEditor5Field(
        "紹介・意気込み", 
        help_text='ライブの見どころが来場者に伝わるように、注目してほしい点やライブの特長を記載する等して工夫して下さい。字数について制限はありませんが、100字程度が理想です。',
        blank=True,
        config_name='extends',
    )
    thumbnail = models.ImageField(
        "サムネイル画像", 
        help_text='アイコン画像として、一覧ページと詳細ページの両方に表示されます。縦横比は1:1が推奨です。設定しない場合は校章アイコン（サンプル）が表示されます。ファイル形式はWebp, PNG, JPG(JPEG)が推奨ですが、その他の画像フォーマットでもアップロード可能です。', 
        upload_to=performance_image_upload_path, 
        blank=True, 
        null=True,
        validators=[validate_image_size],
    )
    thumbnail_avif = ImageSpecField(
        source='thumbnail',
        format='avif',
        options={'quality': 60},
        processors=[ResizeToCover(800, 800)],
    )
    group_photo = models.ImageField(
        "詳細画像", 
        help_text='詳細画像として、詳細ページの「紹介・意気込み」の欄にのみ表示されます。縦横比は4:3が推奨です。設定しない場合は何も表示されません。ファイル形式はWebp, PNG, JPG(JPEG)が推奨ですが、その他の画像フォーマットでもアップロード可能です。', 
        upload_to=performance_image_upload_path, 
        blank=True, 
        null=True,
        validators=[validate_image_size],
    )
    group_photo_avif = ImageSpecField(
        source='group_photo',
        format='avif',
        options={'quality': 60},
        processors=[ResizeToCover(800, 600)],
    )
    spot = models.ForeignKey(Spot, verbose_name="場所", on_delete=models.CASCADE, related_name="performances", limit_choices_to=Q(is_stage=True))
    date = models.ForeignKey("config.FestivalDate", verbose_name="開催日", on_delete=models.CASCADE, related_name="performances", null=True)    #循環import阻止
    begin_at = models.TimeField("開始時刻", null=True)
    end_at = models.TimeField("終了時刻", null=True)
    updated_at = models.DateTimeField("最終更新", auto_now=True)

    @property
    def seconds(self) -> int:
        return (datetime.combine(datetime.today(), self.end_at) - datetime.combine(datetime.today(), self.begin_at)).seconds

    def __str__(self):
        time = f'{self.begin_at}~{self.end_at}'
        if self.spot and self.spot.name == '音楽室':
            time = f'{self.date} {self.begin_at}~{self.end_at}'
        return f'{self.name} {time}'
    
    def clean(self):
        soup = BeautifulSoup(self.message, "html.parser")
        # 不正なタグの検出
        if soup.find("script") or soup.find("link") or soup.find("plaintext") \
            or soup.find("xmp") or soup.find("meta") or soup.find("body") or soup.find("img") or soup.find("form"):
            raise ValidationError({"message": "説明に不正なタグ・要素が含まれています。"})
    
    def save(self, *args, **kwargs):
        self.full_clean()  # バリデーション実行
        if self.pk:
            old = Performance.objects.filter(pk=self.pk).values("token").first()
            if old and old["token"] != self.token:
                # token が変更された場合のみgendatetimeを更新
                self.token_gen_datetime = timezone.now()

        # super().save(*args, **kwargs)
        # 画像をWebPに変換して保存
        if self.thumbnail and not self.thumbnail.name.endswith(".webp"):
            self.thumbnail = convert_to_webp(self.thumbnail, width=500)
        if self.group_photo and not self.group_photo.name.endswith(".webp"):
            self.group_photo = convert_to_webp(self.group_photo, width=1200)
        super().save(*args, **kwargs)  # 圧縮後に再保存

    # サイトマップに必要
    def get_absolute_url(self):
        return reverse("main:performance_detail", args=[str(self.id)])

    class Meta:
        verbose_name = "🇵ライブ🚩"
        verbose_name_plural = "🇵ライブ🚩"
        permissions = [
            ("can_review_performance", "野外ライブ・音楽室ライブの審査権限"),
            ("can_download_performance_review", "野外ライブ・音楽室ライブの差し戻し報告PDFをダウンロードする権限"),
        ]


class Song(SortableModel):
    # ここを明示的に指定しとかないとformsetでエラーが出る
    id = models.BigAutoField(primary_key=True)
    performance = models.ForeignKey(Performance, verbose_name="演奏", on_delete=models.CASCADE, related_name="songs")
    title = models.CharField("曲名", max_length=50)
    artist = models.CharField("アーティスト", max_length=50, blank=True)
    order = models.PositiveSmallIntegerField('順番')

    def __str__(self):
        return f'{self.performance.name} {self.title} {self.artist}'


    class Meta:
        verbose_name = "🇵曲目"
        verbose_name_plural = "🇵曲目"
        ordering = ['order']


class Member(SortableModel):
    # ここを明示的に指定しとかないとformsetでエラーが出る
    id = models.BigAutoField(primary_key=True)
    performance = models.ForeignKey(Performance, verbose_name="演奏", on_delete=models.CASCADE, related_name="members")
    name = models.CharField("ニックネーム", max_length=50)
    instrument = models.CharField("担当楽器", max_length=50, blank=True)
    message = models.CharField("自己紹介・意気込み", max_length=100, blank=True)

    def __str__(self):
        return f'{self.performance.name} {self.name} {self.instrument}'

    class Meta:
        verbose_name = "🇵メンバー🎤"
        verbose_name_plural = "🇵メンバー🎤"
        ordering = ['order']


class Event(SortableModel):
    """主にクラブ展示が行う、期間限定のイベントのモデル
    """
    exhibition = models.ForeignKey(Exhibition, verbose_name="展示", on_delete=models.CASCADE, related_name="events")
    name = models.CharField("イベント名", max_length=50)
    explanation = models.TextField("説明", blank=True)
    spot = models.ForeignKey(Spot, verbose_name="場所", on_delete=models.CASCADE, related_name="events")
    timeslots = models.ManyToManyField(TimeSlot, verbose_name="時間枠", related_name="events", blank=True)

    def __str__(self) -> str:
        return f'{self.exhibition.title} {self.name}'


    class Meta:
        verbose_name = "🇪イベント"
        verbose_name_plural = "🇪イベント"
        ordering = ['order']


# 模擬店
class FoodBooth(models.Model):
    token = models.CharField("トークン", max_length=100, unique=True, default=generate_secure_token)
    token_gen_datetime = models.DateTimeField("トークン生成日時", default=timezone.now)
    name = models.CharField("商品名", max_length=50)
    price = models.PositiveIntegerField("値段", null=True)
    allergens = models.ManyToManyField(Allergens, related_name="foodbooths", blank=True, verbose_name="アレルゲン")
    spot = models.OneToOneField(Spot, verbose_name="場所", on_delete=models.CASCADE, related_name="food_booth", limit_choices_to=Q(floor=Floor.YOUTH_SQUARE), blank=True, null=True)
    thumbnail = models.ImageField(
        "写真",
        upload_to=food_booth_image_upload_path,
        blank=True,
        null=True,
        validators=[validate_image_size],
        )
    thumbnail_avif = ImageSpecField(
            source='thumbnail',
            format='avif',
            options={'quality': 60},
            processors=[ResizeToCover(800, 800)],
        )
    background = models.ImageField(
        "詳細画像", 
        help_text='背景画像として、一覧ページと詳細ページの両方に表示されます。縦横比は4:3が推奨です。設定しない場合は校章アイコン（サンプル）が表示されます。\
            ファイル形式はWebp, PNG, JPG(JPEG)が推奨です。', 
        upload_to=food_booth_image_upload_path, 
        blank=True, 
        null=True,
        validators=[validate_image_size],
    )
    background_avif= ImageSpecField(
        source='background',
        format='avif',
        options={'quality': 60},
        processors=[ResizeToCover(800, 600)],
    )
    message = CKEditor5Field(
        "紹介・意気込み",
        help_text='ライブの見どころが来場者に伝わるように、注目してほしい点やライブの特長を記載する等して工夫して下さい。字数について制限はありませんが、100字程度が理想です。',
        blank=True,
        config_name='extends',
        )
    
    grade_number = models.IntegerField("学年", validators=[MinValueValidator(1), MaxValueValidator(3)])
    class_number = models.IntegerField("クラス", validators=[MinValueValidator(1), MaxValueValidator(10)])
    updated_at = models.DateTimeField("最終更新", auto_now=True)

    def __str__(self):
        return f"{self.grade_number}年{self.class_number}組 {self.name}"

    def clean(self):
        soup = BeautifulSoup(self.message, "html.parser")
        # 不正なタグの検出
        if soup.find("script") or soup.find("link") or soup.find("plaintext") \
            or soup.find("xmp") or soup.find("meta") or soup.find("body") or soup.find("img") or soup.find("form"):
            raise ValidationError({"message": "説明に不正なタグ・要素が含まれています。"})
        
    def save(self, *args, **kwargs):
        self.full_clean()  # バリデーション実行
        if self.pk:
            old = FoodBooth.objects.filter(pk=self.pk).values("token").first()
            if old and old["token"] != self.token:
                # token が変更された場合のみgendatetimeを更新
                self.token_gen_datetime = timezone.now()
        
        # super().save(*args, **kwargs)
        # 画像をWebPに変換して保存
        if self.thumbnail and not self.thumbnail.name.endswith(".webp"):
            self.thumbnail = convert_to_webp(self.thumbnail, width=500)
        if self.background and not self.background.name.endswith(".webp"):
            self.background = convert_to_webp(self.background, width=1200)
        super().save(*args, **kwargs)  # 圧縮後に再保存

    class Meta:
        verbose_name = "模擬店🚩 🍿"
        verbose_name_plural = "🇫模擬店🚩 🍿"
        permissions = [
            ("can_review_food_booth", "模擬店の審査権限"),
            ("can_download_food_booth_review", "模擬店の差し戻し報告PDFをダウンロードする権限"),
        ]


# キッチンカー
class FoodTruck(models.Model):
    name = models.CharField("店名", max_length=50)
    info = models.CharField("紹介", max_length=50, blank=True)
    spot = models.OneToOneField(Spot, verbose_name="場所", on_delete=models.CASCADE, related_name="food_truck", limit_choices_to=Q(floor=Floor.YOUTH_SQUARE), blank=True, null=True)
    picture = models.ImageField(
        "写真",
        upload_to=food_truck_image_upload_path,
        blank=True,
        null=True,
        validators=[validate_image_size],
        )
    picture_avif = ImageSpecField(
            source='picture',
            format='avif',
            options={'quality': 60},
        )
    
    def __str__(self):
        return f'{self.name}'
    
    def save(self, *args, **kwargs):
        self.full_clean()  # バリデーション実行
        # super().save(*args, **kwargs)
        # 画像をWebPに変換して保存
        if self.picture and not self.picture.name.endswith(".webp"):
            self.picture = convert_to_webp(self.picture, width=500)
        super().save(*args, **kwargs)  # 圧縮後に再保存

    class Meta:
        verbose_name = "🇫キッチンカー🚩 🚚"
        verbose_name_plural = "🇫キッチンカー🚩 🚚"
        ordering = ['spot']


class Menu(models.Model):
    food_truck = models.ForeignKey(FoodTruck, verbose_name="キッチンカー", on_delete=models.CASCADE, related_name="menus")
    name = models.CharField("商品名", max_length=50)
    price = models.PositiveIntegerField("値段", blank=True, null=True)
    max_price = models.PositiveIntegerField("最高値段", help_text="設定した場合、<値段>～<最高値段>と表示されます。Ex.) 500円～700円", blank=True, null=True)
    note = models.CharField("備考", max_length=50, blank=True)

    def __str__(self):
        price_str = ""
        if self.max_price:
            price_str = f"{self.price}円～{self.max_price}円"
        else:
            price_str = f"{self.price}円"
        note = ""
        if self.note:
            note = f" ※{self.note}"
        return f"{self.food_truck.name} {self.name} {price_str} {note}"

    class Meta:
        verbose_name = "🇫 メニュー"
        verbose_name_plural = "🇫 メニュー"


class News(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField(max_length=500)
    priority = models.PositiveSmallIntegerField("優先順位", help_text="低いほうがより上に表示されます。（正の数、デフォルト10）", default=10)

    def __str__(self):
        return self.title
    
    class Meta:
        verbose_name = '📰ニュース'
        verbose_name_plural = '📰ニュース'


class ReviewReport(models.Model):
    class ReviewStatus(models.TextChoices):
        REJECTED = "rejected", "差し戻し"
        ACCEPTED = "accepted", "承認済み"
        PENDING = "pending", "審査待ち"

    status = models.CharField("ステータス", max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    reason = models.TextField("差し戻し理由", help_text="差し戻しの理由を記述して下さい。承認する場合は空欄にして下さい。", blank=True)
    reviewed_at = models.DateTimeField("審査日時", help_text="審査を行った日時を示します。", auto_now_add=True)
    in_charge_of = models.CharField("担当の先生", help_text="当該コンテンツの審査担当の先生のお名前です。生徒が問い合わせや相談をする際に参考になります。",)
    
    class Meta:
        abstract = True


class ExhibitionReviewReport(ReviewReport):
    """展示の審査報告
    """
    exhibition = models.ForeignKey(Exhibition, verbose_name="展示", on_delete=models.CASCADE, related_name="review_reports")

    def __str__(self):
        return f"審査ログ {self.exhibition.title} - {self.reason[:20]}"

    class Meta:
        verbose_name = "🇪 展示審査"
        verbose_name_plural = "🇪 展示審査"


class PerformanceReviewReport(ReviewReport):
    """ライブの審査報告
    """
    performance = models.ForeignKey(Performance, verbose_name="ライブ", on_delete=models.CASCADE, related_name="review_reports")

    def __str__(self):
        return f"審査ログ {self.performance.name} - {self.reason[:20]}"

    class Meta:
        verbose_name = "🇵 ライブ審査"
        verbose_name_plural = "🇵 ライブ審査"


class FoodBoothReviewReport(ReviewReport):
    """模擬店の審査報告
    """
    food_booth = models.ForeignKey(FoodBooth, verbose_name="模擬店", on_delete=models.CASCADE, related_name="review_reports")

    def __str__(self):
        return f"審査ログ {self.food_booth.name} - {self.reason[:20]}"

    class Meta:
        verbose_name = "🇫 模擬店審査"
        verbose_name_plural = "🇫 模擬店審査"


class YouthSquareMap(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    day1_original = models.ImageField("１日目", upload_to=general_image_upload_path, blank=False, null=True, default="")
    day1 = ImageSpecField(
        source='day1_original',
        format='webp',
        options={'quality': 60},
    )
    day2_original = models.ImageField("２日目", upload_to=general_image_upload_path, blank=False, null=True, default="")
    day2 = ImageSpecField(
        source='day2_original',
        format='webp',
        options={'quality': 60},
    )

    class Meta:
        verbose_name = "🗺️青春の広場の地図"
        verbose_name_plural = "🗺️青春の広場の地図"
