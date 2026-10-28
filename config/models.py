from django.db import models

from django_ckeditor_5.fields import CKEditor5Field
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import ASCIIUsernameValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.functional import cached_property
from datetime import datetime
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit
from pathlib import Path

import uuid, requests

from main.convert import convert_to_webp, validate_image_size
# from main.models import User


def user_icon_upload_path(instance, filename):
    return f"images/users/icon/{instance.user_id}{Path(filename).suffix}"

def user_header_upload_path(instance, filename):
    return f"images/users/header/{instance.user_id}{Path(filename).suffix}"

# 日時を元に一意の画像名を生成　Ex.) "20240209-232853820291"
def get_random_name():
    return datetime.now().strftime("%Y%m%d-%H%M%S%f")

# Create your models here.
def image_upload_path(instance, filename):
    return f"theme/{get_random_name()}{Path(filename).suffix}"


class User(AbstractUser):
    user_id = models.CharField(
        "ユーザーID",
        max_length=150,
        unique=True,
        help_text="ユーザーID。この項目は必須です。半角アルファベット、半角数字、@/./+/-/_ で150文字以下にしてください。",
        validators=[ASCIIUsernameValidator()],
    )
    username = models.CharField(
        "ユーザー名",
        max_length=150,
        unique=True,
        help_text="ユーザー名。この項目は必須です。日本語で150文字以下にしてください。",
    )
    is_ya_user = models.BooleanField(
        "Яの利用権限",
        default=False,
    )
    is_developer = models.BooleanField(
        "開発者かどうか",
        default=False,
    )

    role = models.ForeignKey('ya.YaUserRole', verbose_name="Яの役割", on_delete=models.SET_NULL, null=True, blank=True)
    self_introduction = CKEditor5Field(
        "自己紹介", 
        help_text='自己紹介', 
        blank=True,
        config_name='extends'   #settingsのextends設定を使用
    )

    def get_role_icon(self):
        if self.role:
            return self.role.icon
        return ""

    friends = models.ManyToManyField('self', symmetrical=False, related_name='following', blank=True)
    icon = models.ImageField(
        "画像",
        upload_to=user_icon_upload_path,
        blank=True,
        null=True,
        validators=[validate_image_size],
        )
    
    header_image = models.ImageField(
        "アカウントヘッダー画像",
        upload_to=user_header_upload_path,
        blank=True,
        null=True,
        help_text="プロフィールの上部に表示される背景画像です。",
        validators=[validate_image_size],
    )

    header_image_avif = ImageSpecField(
        source='header_image',
        format='avif',
        options={'quality': 60},
    )
    
    USERNAME_FIELD = "user_id"
    REQUIRED_FIELDS = ['username', ] # REQUIRED_FIELDS は createsuperuser コマンドで利用される

    def __str__(self) -> str:
        return f'{self.username} (ID: {self.user_id})'
    
    def save(self, *args, **kwargs):
        # 最初に一度保存して、ファイルの実体を確定させる
        # super().save(*args, **kwargs)
        
        # アイコンをWebP変換
        if self.icon and not self.icon.name.endswith(".webp"):
            self.icon = convert_to_webp(self.icon, width=500)
        
        # ヘッダー画像をWebP変換（横幅1200px程度にリサイズ）
        if self.header_image and not self.header_image.name.endswith(".webp"):
            self.header_image = convert_to_webp(self.header_image, width=1200)
            
        # 変換後に再度保存
        super().save(*args, **kwargs)

    @property
    def unread_notification_count(self):
        # 自身宛の通知(notifications)のうち、is_readがFalseの数を返す
        return self.notifications.filter(is_read=False).count()

    class Meta:
        verbose_name = "👥ユーザー"
        verbose_name_plural = "👥ユーザー"


class Slogan(models.Model):
    year = models.SmallIntegerField("年度", null=True)
    main = models.CharField("スローガン(メイン)", max_length=50)
    sub = models.CharField("スローガン(サブ)", max_length=50)
    image1 = models.ImageField(
        "キーアート",
        upload_to=image_upload_path,
        blank=True,
        null=True,
        validators=[validate_image_size],
        )
    footer_image = models.ImageField(
        "フッター写真",
        upload_to=image_upload_path,
        blank=True,
        null=True,
        validators=[validate_image_size],
        )
    
    def __str__(self) -> str:
        return f'{self.year}年度：{self.main} ―{self.sub}―'
    
    def save(self, *args, **kwargs):
        self.full_clean()  # バリデーション実行
        # super().save(*args, **kwargs)
        # 画像をWebPに変換して再保存
        if self.image1 and not self.image1.name.endswith(".webp"):
            self.image1 = convert_to_webp(self.image1, width=1200)
        if self.footer_image and not self.footer_image.name.endswith(".webp"):
            self.footer_image = convert_to_webp(self.footer_image, width=1200)
        super().save(*args, **kwargs)  # 圧縮後に再保存
    
    class Meta:
        verbose_name = "🎨文化祭スローガン・キーアート"
        verbose_name_plural = "🎨文化祭スローガン・キーアート"


class FestivalDate(models.Model):
    day = models.PositiveSmallIntegerField("何日目か")
    begin_at = models.DateTimeField("開始時刻")
    end_at = models.DateTimeField("終了時刻")

    @property
    def begin_at_time(self) -> str:
        dt = self.begin_at.astimezone(timezone.get_current_timezone())
        return f"{dt.hour}:{dt.strftime('%M')}"

    @property
    def end_at_time(self) -> str:
        dt = self.end_at.astimezone(timezone.get_current_timezone())
        return f"{dt.hour}:{dt.strftime('%M')}"

    @property
    def seconds(self) -> int:
        return (self.end_at - self.begin_at).seconds

    def __str__(self) -> str:
        return f'{self.day}日目'

    class Meta:
        verbose_name = "📅開催日"
        verbose_name_plural = "📅開催日"


class Sports_FesInfo(models.Model):
    year = models.SmallIntegerField("年度", null=True, unique=True)
    begin_at = models.DateTimeField("開始時刻")
    end_at = models.DateTimeField("終了時刻")
    main = models.CharField("スローガン(メイン)", max_length=50)
    sub = models.CharField("スローガン(サブ)", max_length=50)
    
    def __str__(self) -> str:
        return f'{self.year}年度：{self.main} ―{self.sub}―'
    
    class Meta:
        verbose_name = "🏃‍♂️‍➡️体育祭スローガン・開催日"
        verbose_name_plural = "🏃‍♂️‍➡️体育祭スローガン・開催日"


class Permission(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    display_home = models.BooleanField('[文化祭]ホームの表示', default=False)
    display_introduction = models.BooleanField('[文化祭]紹介ページの表示', default=False)

    can_edit_exhibitions = models.BooleanField('[文化祭]展示紹介ページの編集を許可', default=True)
    can_edit_performances = models.BooleanField('[文化祭]ライブ紹介ページの編集を許可', default=True)
    can_edit_attractions = models.BooleanField('[文化祭]展示紹介ページの編集を許可（当日入力用）', default=True)
    can_edit_foodbooth = models.BooleanField('[文化祭]模擬店の編集を許可', default=True)
    
    display_sports_fes = models.BooleanField('[体育祭]ページの表示（一括）', default=False)
    can_edit_team_info = models.BooleanField('[体育祭]応援団ページ編集を許可', default=True)
    
    beta_status = models.BooleanField('ベータかどうか（開発中かリリース版か）', default=True)
    
    # 編集期限の設定
    exhibitions_editing_deadline = models.DateTimeField('展示編集期限（DBの変更時刻）')
    exhibitions_editing_deadline_scheduled = models.BooleanField('（展示）上の編集期限での変更をスケジュールする', default=False)
    food_booths_editing_deadline = models.DateTimeField('模擬店編集期限（DBの変更時刻）')
    food_booths_editing_deadline_scheduled = models.BooleanField('（模擬店）上の編集期限での変更をスケジュールする', default=False)
    performances_editing_deadline = models.DateTimeField('ライブ編集期限（DBの変更時刻）')
    performances_editing_deadline_scheduled = models.BooleanField('（ライブ）上の編集期限での変更をスケジュールする', default=False)
    # 公開日時
    publishing_datetime = models.DateTimeField('公開日時（DBの変更時刻）')
    publishing_datetime_scheduled = models.BooleanField('上の日時での公開をスケジュールする', default=False)
    # 展示の当日編集
    allow_attraction_create_datetime = models.DateTimeField('当日編集の可能になる時刻（DBの変更時刻）')
    allow_attraction_create_datetime_scheduled = models.BooleanField('上の時刻での変更をスケジュールする', default=False)
    
    map_key = models.CharField("Mapを見るための合言葉", max_length=30)
    
    def save(self, *args, **kwargs):
        if not self.pk and Permission.objects.exists():
            return
        return super().save(*args, **kwargs)
    
    def __str__(self):
        str = []
        if self.display_home:
            str.append("文化祭公開中")
        if self.display_introduction:
            str.append("紹介公開中")
        if self.display_sports_fes:
            str.append("体育祭公開中")
        if self.can_edit_exhibitions:
            str.append("展示編集可")
        if self.can_edit_foodbooth:
            str.append("模擬店編集可")
        if self.can_edit_performances:
            str.append("ライブ編集可")
        if self.can_edit_attractions:
            str.append("展示当日分編集可")
        return f"{', '.join(str)}"
    
    class Meta:
        verbose_name = "🔒権限管理"
        verbose_name_plural = "🔒権限管理"


class Credit(models.Model):
    name = models.CharField('お名前', max_length=30)
    is_developer = models.BooleanField('開発者かどうか', blank=False, default=False)
    contribution = models.CharField('貢献', max_length=20, help_text='写真・アイコン作成など、どんな貢献・担当だったか', blank=True)
    words = models.TextField('一言', max_length=120)

    class Meta:
        verbose_name = "©クレジット"
        verbose_name_plural = "©クレジット"


class Images(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    header_index = models.ImageField("ホーム画面の写真", upload_to=image_upload_path, blank=False, null=True, default="", validators=[validate_image_size],)
    header_index_avif= ImageSpecField(
        source='header_index',
        format='avif',
        options={'quality': 60},
        processors=[ResizeToFit(width=1920)],
    )
    header_function = models.ImageField("header.functionの写真", upload_to=image_upload_path, blank=False, null=True, default="", validators=[validate_image_size],)
    header_function_avif= ImageSpecField(
        source='header_function',
        format='avif',
        options={'quality': 60},
        processors=[ResizeToFit(width=1920)],
    )
    header_exhibitions = models.ImageField("展示画面の写真", upload_to=image_upload_path, blank=False, null=True, default="", validators=[validate_image_size],)
    header_exhibitions_avif= ImageSpecField(
        source='header_exhibitions',
        format='avif',
        options={'quality': 60},
        processors=[ResizeToFit(width=1920)],
    )
    header_youthsquare = models.ImageField("青春の広場の写真", upload_to=image_upload_path, blank=False, null=True, default="", validators=[validate_image_size],)
    header_youthsquare_avif= ImageSpecField(
        source='header_youthsquare',
        format='avif',
        options={'quality': 60},
        processors=[ResizeToFit(width=1920)],
    )
    header_performances = models.ImageField("ライブ画面の写真", upload_to=image_upload_path, blank=False, null=True, default="", validators=[validate_image_size],)
    header_performances_avif= ImageSpecField(
        source='header_performances',
        format='avif',
        options={'quality': 60},
        processors=[ResizeToFit(width=1920)],
    )
    header_coming_soon = models.ImageField("Coming_soon画面の写真", upload_to=image_upload_path, blank=False, null=True, default="", validators=[validate_image_size],)
    header_coming_soon_avif= ImageSpecField(
        source='header_coming_soon',
        format='avif',
        options={'quality': 60},
        processors=[ResizeToFit(width=1920)],
    )

    def save(self, *args, **kwargs):
        self.full_clean()  # バリデーション実行
        # super().save(*args, **kwargs)
        # 画像をWebPに変換して再保存
        if self.header_index and not self.header_index.name.endswith(".webp"):
            self.header_index = convert_to_webp(self.header_index, width=1920)
        if self.header_function and not self.header_function.name.endswith(".webp"):
            self.header_function = convert_to_webp(self.header_function, width=1920)
        if self.header_exhibitions and not self.header_exhibitions.name.endswith(".webp"):
            self.header_exhibitions = convert_to_webp(self.header_exhibitions, width=1920)
        if self.header_youthsquare and not self.header_youthsquare.name.endswith(".webp"):
            self.header_youthsquare = convert_to_webp(self.header_youthsquare, width=1920)
        if self.header_performances and not self.header_performances.name.endswith(".webp"):
            self.header_performances = convert_to_webp(self.header_performances, width=1920)
        if self.header_coming_soon and not self.header_coming_soon.name.endswith(".webp"):
            self.header_coming_soon = convert_to_webp(self.header_coming_soon, width=1920)
        super().save(*args, **kwargs)  # 圧縮後に再保存

    class Meta:
        verbose_name = "🖼ヘッダー等の写真"
        verbose_name_plural = "🖼ヘッダー等の写真"


class DefaultCounts(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    live_stage_count = models.SmallIntegerField("DB初期化の際生成する、野外ライブのオブジェクト数")
    music_room_count = models.SmallIntegerField("DB初期化の際生成する、音楽室ライブのオブジェクト数")

    class Meta:
        verbose_name = "💾デフォルトオブジェクト数"
        verbose_name_plural = "💾デフォルトオブジェクト数"


class LogLevels(models.TextChoices):
    DEBUG = "debug", "デバッグ"
    INFO = "info", "情報"
    WARNING = "warning", "警告"
    ERROR = "error", "エラー"
    FATAL = "fatal", "致命的"


class EC2OperationsLog(models.Model):
    datetime = models.DateTimeField("実行時間", auto_now_add=True, )
    user = models.ForeignKey("config.User", on_delete=models.CASCADE, )
    log_level = models.CharField("ログレベル", choices=LogLevels.choices, default=LogLevels.INFO)
    command = models.CharField("実行したコマンド", max_length=200, )
    response = models.TextField("レスポンス", )
    exit_code = models.IntegerField("終了コード", default=1)

    def __str__(self):
        return f"{self.user} : {self.command}"

    class Meta:
        verbose_name = "💻EC2操作ログ"
        verbose_name_plural = "💻EC2操作ログ"


class FeedBackFormURL(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    url = models.CharField("感想フォームのURL", max_length=254)

    class Meta:
        verbose_name = "📋感想フォームURL"
        verbose_name_plural = "📋感想フォームURL"

    def save(self, *args, **kwargs):
        if not self.pk and Permission.objects.exists():
            return
        return super().save(*args, **kwargs)


class NewDomainRedirectURL(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    url = models.URLField("新しいドメインのURL", help_text="新年度、新しいURLに移行する際、古いドメイン側で設定します。", blank=True)
    active = models.BooleanField(
        "移行シークエンスの状態", default=False, 
        help_text="警告：一度有効にすると、手動でDBを変更しない限り、全てのリクエストが新しいURLにリダイレクトされるため、Webで現在のドメインへのアクセスができなくなります。")

    def clean(self):
        if self.url == "" and self.active == False: #未設定の場合はOK
            return
        try:
                response = requests.get(self.url, timeout=3)
                response.raise_for_status() #不正ならここで例外
        except requests.exceptions.RequestException as e:
            raise ValidationError("正常に到達できない、不正なURLです。")

    class Meta:
        verbose_name = "🤝新ドメイン移行用URL設定"
        verbose_name_plural = "🤝新ドメイン移行用URL設定"
