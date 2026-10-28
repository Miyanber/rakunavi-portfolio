from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from io import BytesIO
import os
from PIL import Image, ImageOps

# そもそもなぜ、JSだけでなくサーバーでもvalidateするか：サイバー攻撃やハックに備えるため

def validate_image_size(image):
    max_size_mb = 5  # 上限サイズ
    if image.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"画像サイズは {max_size_mb}MB 以下にしてください。")
    
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import os


def convert_to_webp(image_field, width=None, quality=80):
    """
    ImageField を WebP に変換して保存
    :param image_field: Django ImageField
    :param width: 横幅のみ指定（縦はアスペクト比維持）
    :param quality: WebP 品質
    """
    if not image_field:
        return None

    image_field.file.seek(0)
    img = Image.open(image_field.file)
    img = ImageOps.exif_transpose(img)

    # RGBA → RGB
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 横幅指定がある場合 → アスペクト比維持でリサイズ
    if width:
        w_percent = width / float(img.size[0])
        height = int(float(img.size[1]) * w_percent)
        img = img.resize((width, height), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="WEBP", optimize=True, quality=quality)
    buffer.seek(0)

    new_name = os.path.splitext(image_field.name)[0] + ".webp"

    return ContentFile(buffer.read(), name=new_name)
