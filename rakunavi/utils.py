import qrcode
from io import BytesIO
import base64
import re


def generate_qr_base64(url: str) -> str:
    """
    指定されたURLからQRコードを作成する。
    """
    if url.startswith('/'):
        # 相対パスの場合 QR コードが機能しないため警告を出す
        print("Warning: URL starts with '/', which may not be valid for QR code generation.")
    qr = qrcode.make(url)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def sanitize_filename(filename: str, replacement: str = "_") -> str:
    # 禁止文字（Windows + Unix系共通で安全な範囲にする）
    invalid_chars = r'[<>:"/\\|?*\x00]'  # \x00 = NULL文字
    sanitized = re.sub(invalid_chars, replacement, filename)

    # Windows予約語チェック（拡張子ついててもNG）
    reserved_names = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }

    # 拡張子を一旦除外してベース名をチェック
    base, *ext = sanitized.split(".")
    if base.upper() in reserved_names:
        base += "_"

    # 拡張子があればつけ直す
    if ext:
        return base + "." + ".".join(ext)
    else:
        return base