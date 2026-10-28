from django.db import models

from django_ckeditor_5.fields import CKEditor5Field
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils import timezone
from datetime import datetime
from imagekit.models import ImageSpecField
from bs4 import BeautifulSoup
from pathlib import Path

from main.convert import convert_to_webp, validate_image_size
from config.models import get_random_name

import uuid

def posts_image_upload_path(instance, filename):
    return f"images/ya/posts/{get_random_name()}{Path(filename).suffix}"

class ChatGroups(models.Model):
    name = models.CharField("グループ名", max_length=50, help_text="グループ名")
    created_at = models.DateTimeField("作成日", auto_now_add=True)
    members = models.ManyToManyField(User, related_name="members", verbose_name="メンバー", help_text="メンバー")
    image = models.ImageField(
        "画像",
        upload_to=posts_image_upload_path,
        blank=True,
        null=True,
        validators=[validate_image_size],
        )
    image_avif = ImageSpecField(
        source='image',
        format='avif',
        options={'quality': 60},
    )
    description = models.TextField("説明", help_text="このグループの説明", blank=True, null=True,)
    material_icon = models.CharField("Material Icon Roundedの指定", max_length=50, default="groups")
    is_visible = models.BooleanField("可視性", default=True)

    def save(self, *args, **kwargs):
        self.full_clean()  # バリデーション実行
        if self.image and not self.image.name.endswith(".webp"):
            self.image = convert_to_webp(self.image, width=1920)
        super().save(*args, **kwargs)  # 圧縮後に再保存

    def __str__(self):
        return f"{self.name}({self.members.count()})"

    class Meta:
        verbose_name = "チャットグループ"
        verbose_name_plural = "チャットグループ"


class ChatMessages(models.Model):
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sent_messages"
    )
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE,
        blank=True, null=True, related_name="received_messages"
    )
    receiver_group = models.ForeignKey(
        ChatGroups, on_delete=models.CASCADE,
        blank=True, null=True, related_name="messages"
    )
    read_by = models.ManyToManyField(
        User, related_name="read_messages", blank=True
    )

    content = models.TextField()
    send_at = models.DateTimeField(auto_now_add=True, db_index=True)
    is_visible = models.BooleanField("可視性", default=True)

    def clean(self):
        if len(self.content) > 1000:
            raise ValidationError({"content": "文字数が多すぎます。"})
        if self.receiver and self.receiver_group:
            raise ValidationError("receiver と receiver_group は同時に指定できません")
        if not self.receiver and not self.receiver_group:
            raise ValidationError("receiver または receiver_group のどちらかは必須")

    def save(self, *args, **kwargs):
        self.full_clean() #これがないとバリデーションが呼ばれない
        super().save(*args, **kwargs)

    def is_dm(self):
        return self.receiver is not None

    def is_group(self):
        return self.receiver_group is not None
    
    def __str__(self):
        if self.receiver:
            return f"{self.sender.username} → {self.receiver.username}：{self.content}"
        return f"{self.sender.username} → {self.receiver_group.name}：{self.content}"


class Post(models.Model):
    author = models.ForeignKey(User, verbose_name="作成者", on_delete=models.CASCADE, related_name="posts")
    reply_to = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='replies', # post.replies.all() で返信一覧を取得可能
        verbose_name="返信先"
    )
    content = CKEditor5Field(
        "内容", 
        help_text='内容',
        config_name='safer',
    )
    image = models.ImageField(
        "画像",
        upload_to=posts_image_upload_path,
        blank=True,
        null=True,
        validators=[validate_image_size],
        )
    image_avif = ImageSpecField(
        source='image',
        format='avif',
        options={'quality': 60},
    )
    created_at = models.DateTimeField("作成日", auto_now_add=True, db_index=True)
    is_visible = models.BooleanField("可視性", default=True)
    liked = models.ManyToManyField(User, related_name="liked", verbose_name="いいね", help_text="いいね", blank=True)
    submit_token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True,
    )

    def save(self, *args, **kwargs):
        self.full_clean()  # バリデーション実行
        if self.image and not self.image.name.endswith(".webp"):
            self.image = convert_to_webp(self.image, width=1920)
        super().save(*args, **kwargs)  # 圧縮後に再保存

    def clean(self):
        if len(self.content) > 5000:
            raise ValidationError({"content": "コンテンツが多すぎます。"})
        soup = BeautifulSoup(self.content, "html.parser")
        # まず空のタグを消去
        for tag in soup.find_all():
            if not tag.get_text(strip=True):
                tag.decompose()
        if not soup.find_all():
            raise ValidationError({"content": "内容が空です。"})
        # 不正なタグの検出 XSS対策
        if soup.find("script") or soup.find("link") or soup.find("plaintext") \
            or soup.find("xmp") or soup.find("meta") or soup.find("body") or soup.find("form"):
            raise ValidationError({"content": "説明に不正なタグ・要素が含まれています。"})
    
    def __str__(self):
        return f"{self.author.username}：{self.content}"

    class Meta:
        verbose_name = "投稿"
        verbose_name_plural = "投稿"


class YaUserRole(models.Model):
    name = models.CharField("ロール名", max_length=50, unique=True)
    icon = models.CharField("Material Icon 名", max_length=50)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "ロール"
        verbose_name_plural = "ロール"


class YaSettings(models.Model):
    beta = models.BooleanField("Betaかどうか", help_text="Betaかどうか示します。" , default=True)
    
    def __str__(self):
        if self.beta:
            return f"BETA版"
        return "運用版"
    
    class Meta:
        verbose_name = "Яの設定"
        verbose_name_plural = "Яの設定"


class Notification(models.Model):
    # 通知の種類を定義
    ACTION_CHOICES = (
        ('like', 'いいね'),
        ('reply', '返信'),
    )

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_notifications", verbose_name="アクションした人")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications", verbose_name="通知を受け取る人")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="notification_post", verbose_name="対象の投稿")
    action_type = models.CharField("アクションの種類", max_length=10, choices=ACTION_CHOICES)
    is_read = models.BooleanField("既読フラグ", default=False)
    created_at = models.DateTimeField("通知日時", auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "通知"
        verbose_name_plural = "通知"
