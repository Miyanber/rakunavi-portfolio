# created by ChatGPT（一部）
# db.sqlite3 からデータベースを復元するスクリプト
# 使用方法・利用例は docs/script_introduction.md を参照してください。

import sys
from pathlib import Path
import shutil

import sys
from pathlib import Path
import shutil

def load_db():
    # 引数チェック
    # --- 設定 ---
    DEFAULT_TARGET = Path("db.sqlite3")

    # --- 引数処理 ---
    if len(sys.argv) == 1 or len(sys.argv) > 3:
        print("引数を正しく指定して下さい。")
        print("使用方法: python restore_db.py <DBファイルのパス> [--force]")
        sys.exit(1)

    backup_path_row = sys.argv[1]
    if not backup_path_row.endswith(".sqlite3"):
        print("DBファイルは .sqlite3 拡張子である必要があります。")
        sys.exit(1)
    backup_path_row = backup_path_row.replace("\\", "/")  # Windowsのパスを正規化
    backup_path = Path(backup_path_row)
    force_overwrite = "--force" in sys.argv  # 上書き強制オプション

    # --- 存在確認 ---
    if not backup_path.exists():
        print(f"DBファイルが見つかりません: {backup_path}")
        sys.exit(1)

    # --- 上書き確認 or 中止 ---
    if DEFAULT_TARGET.exists():
        if not force_overwrite:
            print(f"既存のDBファイルが存在します: {DEFAULT_TARGET}")
            print("    上書きしたい場合は `--force` を付けてください。")
            sys.exit(1)
        else:
            print(f"既存のDBを削除します: {DEFAULT_TARGET}")
            DEFAULT_TARGET.unlink()

    # --- DBファイルからリストア ---
    print(f"DBファイルからリストア中: {backup_path} → {DEFAULT_TARGET}")
    shutil.copy(backup_path, DEFAULT_TARGET)

    print("リストア完了！")

if __name__ == "__main__":
    load_db()