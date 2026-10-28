from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django_ckeditor_5.fields import CKEditor5Field

from main.models import generate_secure_token


# ---------------------------------------------------------------------------
# 学年色
#   grade_num: 1=中1 … 3=中3, 4=高1 … 6=高3
#   管理コマンド sports_fes_init_grade_colors で一括生成可能
# ---------------------------------------------------------------------------
class GradeColor(models.Model):
    GRADE_CHOICES = [
        (1, "中1"), (2, "中2"), (3, "中3"),
        (4, "高1"), (5, "高2"), (6, "高3"),
        (7, "その他"), #375で変更
    ]
    grade_num = models.SmallIntegerField(
        "学年", unique=True, choices=GRADE_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(7)], #375で変更
    )
    color = models.CharField("カラーコード（#抜き）", max_length=6, default="cccccc")

    def __str__(self):
        return f"{self.get_grade_num_display()} #{self.color}"

    class Meta:
        ordering = ["grade_num"]
        verbose_name = verbose_name_plural = "🎨学年色"


# ---------------------------------------------------------------------------
# 学級マスタ
#   学校全体のクラス一覧。management command `init_school_classes` で一括生成。
# ---------------------------------------------------------------------------
class SchoolClass(models.Model):
    GRADE_CHOICES = [
        (1, "中1"), (2, "中2"), (3, "中3"),
        (4, "高1"), (5, "高2"), (6, "高3"),
    ]

    grade_num = models.SmallIntegerField(
        "学年", choices=GRADE_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(6)],
    )
    class_num = models.SmallIntegerField(
        "クラス",
        validators=[MinValueValidator(1)],
    )

    class Meta:
        unique_together = [("grade_num", "class_num")]
        ordering = ["grade_num", "class_num"]
        verbose_name = "学級"
        verbose_name_plural = "🏫学級マスタ"

    def __str__(self):
        return f"{self.get_grade_num_display()}-{self.class_num}"


# ---------------------------------------------------------------------------
# 応援団
#   1クラスが複数団に属せないよう Admin / clean() で制御する。
#   prefetch_related("classes") 済みの状態で get_grade_blocks() を呼ぶこと。
# ---------------------------------------------------------------------------
class Team(models.Model):
    TEAM_CHOICES = [("red", "赤団"), ("blue", "青団"), ("yellow", "黄団")]

    name = models.CharField(max_length=10, choices=TEAM_CHOICES, unique=True)
    description = CKEditor5Field(
        "説明文",
        help_text = "詳細はマニュアルを参照してください。",
        blank=True,
        null=True,
        config_name='extends',
        )
    main_image = models.ImageField("メイン画像", upload_to="sports_fes/team_images/", blank=True, null=True)
    bg_image = models.ImageField("背景画像", upload_to="sports_fes/team_backgrounds/", blank=True, null=True)
    classes = models.ManyToManyField(
        SchoolClass,
        blank=True,
        verbose_name="所属学級",
        related_name="teams",
    )
    points = models.SmallIntegerField("得点", default=0)
    win = models.BooleanField("優勝か否か", default=False)
    points_updated_at = models.DateTimeField("得点更新時間", auto_now=True)
    token = models.CharField("トークン", max_length=100, unique=True, default=generate_secure_token)

    def get_grade_blocks(self) -> list[dict]:
        middle: dict[int, list[int]] = {}
        high: dict[int, list[int]] = {}

        for sc in self.classes.all():
            g = sc.grade_num
            if g <= 3:
                middle.setdefault(g, []).append(sc.class_num)
            else:
                high.setdefault(g, []).append(sc.class_num)

        blocks = []
        if middle:
            blocks.append({
                "label": "中学",
                "groups": [
                    {"grade_num": g, "class_nums": sorted(nums)}
                    for g, nums in sorted(middle.items())
                ],
            })
        if high:
            blocks.append({
                "label": "高校",
                "groups": [
                    {"grade_num": g - 3, "class_nums": sorted(nums)}
                    for g, nums in sorted(high.items())
                ],
            })
        return blocks

    def __str__(self):
        return dict(self.TEAM_CHOICES).get(self.name, self.name)

    class Meta:
        verbose_name = verbose_name_plural = "📢応援団"



# ---------------------------------------------------------------------------
# プログラム
#   grades: 学年番号のリスト [1,2,3,4,5,6] を JSONField で管理。
# ---------------------------------------------------------------------------
class Program(models.Model):
    MORNING = "AM"
    AFTERNOON = "PM"
    SESSION_CHOICES = [(MORNING, "午前の部"), (AFTERNOON, "午後の部")]

    GRADE_CHOICES = [
        (1, "中1"), (2, "中2"), (3, "中3"),
        (4, "高1"), (5, "高2"), (6, "高3"),
        (7, "その他"),
    ] #375で変更

    session = models.CharField(max_length=2, choices=SESSION_CHOICES)
    number = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=100)
    # [1, 3, 5] のように学年番号を直接格納。空リスト = 全学年対象
    grades = models.JSONField(
        "対象学年", default=list, blank=True,
        help_text="例: [1,2,3] ← 中1〜中3対象。空 = 全学年。",
    )
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="sports_fes/program_images/", blank=True, null=True)
    track_image = models.ImageField(upload_to="sports_fes/track_images/", blank=True, null=True)

    # 対象学年の表示名リストを返す
    def grade_labels(self) -> list[str]:
        label_map = dict(self.GRADE_CHOICES)
        return [label_map[g] for g in self.grades if g in label_map]

    class Meta:
        ordering = ["session", "number"]
        verbose_name = verbose_name_plural = "📚プログラム"

    def __str__(self):
        return f"{self.session} {self.number} {self.name}"

    @property
    def target_grades(self):
        if not self.grades:
            return [1, 2, 3, 4, 5, 6]

        return [int(g) for g in self.grades] #375で追加

# ---------------------------------------------------------------------------
# 会場案内
# ---------------------------------------------------------------------------
class FieldGuide(models.Model):
    image = models.ImageField("会場案内画像", upload_to="sports_fes/images/")

    def __str__(self):
        return self.image.name

    class Meta:
        verbose_name = verbose_name_plural = "🕶️会場案内画像"


class Facility_Alt(models.Model):
    alt = CKEditor5Field(
        "説明",
        help_text="会場案内の説明文",
        blank=True,
        config_name="extends",
    )

    class Meta:
        verbose_name = verbose_name_plural = "👮会場案内の説明文"


# ---------------------------------------------------------------------------
# 近鉄ダイヤ
# ---------------------------------------------------------------------------
class KintetsuSchedule(models.Model):
    bound_for = models.CharField("行き先", max_length=20)
    Kyoto_Departure_Time = models.TimeField("京都駅発")
    Tanbabashi_Departure_Time = models.TimeField("丹波橋駅発")
    Mukaijima_Departure_Time = models.TimeField("向島駅発")

    class Meta:
        verbose_name = verbose_name_plural = "🚃近鉄電車特別ダイヤ"

class KintetsuExplanation(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    content = CKEditor5Field(
            "説明",
            help_text="近鉄の説明文",
            blank=True,
            config_name="extends",
            )
    show_schedule = models.BooleanField("ダイヤを表示する", default=True)

    class Meta:
            verbose_name = verbose_name_plural = "🚃近鉄電車に関しての説明"


# ---------------------------------------------------------------------------
# 一般画像（サイト全体で1レコードのみ使用）
# ---------------------------------------------------------------------------
class GeneralImages(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    index_title = models.ImageField("Indexのトップ画像", null=True, blank=True, upload_to="sports_fes/images/")
    index_dark_title = models.ImageField("Indexのダークモードトップ画像", null=True, blank=True, upload_to="sports_fes/images/") #375で追加
    slogan_image = models.ImageField(
        "スローガン画像", upload_to="sports_fes/images/", null=True, blank=True
    ) #375で追加
    slogan_dark_image = models.ImageField(
        "スローガンダークモード画像", upload_to="sports_fes/images/", null=True, blank=True,
    ) #375で追加
    slogan_logo = models.ImageField(
        "スローガンロゴ", upload_to="sports_fes/images/", null=True, blank=True,
    ) #375で追加
    slogan_dark_logo = models.ImageField(
        "スローガンダークモードロゴ", upload_to="sports_fes/images/", null=True, blank=True,
    ) #375で追加
    program_header = models.ImageField("プログラムヘッダー画像", null=True, blank=True, upload_to="sports_fes/images/")
    team_header = models.ImageField("チームヘッダー画像", null=True, blank=True, upload_to="sports_fes/images/")
    facility_header = models.ImageField(
        "会場案内ヘッダー画像", upload_to="sports_fes/images/", null=True, blank=True
    )
    access_header = models.ImageField(
        "アクセスヘッダー画像", upload_to="sports_fes/images/", null=True, blank=True
    )
    fieldguide = models.ImageField("会場案内画像", null=True, blank=True, upload_to="sports_fes/images/")

    class Meta:
        verbose_name = verbose_name_plural = "🖼️一般画像"
