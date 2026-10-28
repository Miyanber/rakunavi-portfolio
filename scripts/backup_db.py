# created by ChatGPT（一部）
# db.sqlite3 からデータベースのバックアップを作成するスクリプト
# 使用方法・利用例は docs/script_introduction.md を参照してください。

from colorama import init, Fore, Style
init(autoreset=True)
import sys
import subprocess
from pathlib import Path
from datetime import datetime
import shutil

def backup_db(prefix = "db"):

    def get_git_info():
        try:
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], stderr=subprocess.DEVNULL
            ).decode().strip()
            commit = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            ).decode().strip()
        except Exception:
            branch, commit = "no-branch", "no-commit"
        return branch.replace("/", "_"), commit

    branch, commit = get_git_info()

    db_path = Path("db.sqlite3")
    backup_dir = Path("db_files")
    backup_dir.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = backup_dir / branch
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"{prefix}_{timestamp}_commit_{commit}.sqlite3"
        print(f"データベースをバックアップ中: {db_path} → {backup_path}")
        shutil.copy(db_path, backup_path)
    else:
        print(Fore.RED + "バックアップ対象のDBファイルが存在しません。")

    # DBマイグレーション
    print(Fore.GREEN + "完了しました。")


if __name__ == "__main__":
    prefix = sys.argv[1] if len(sys.argv) > 1 else "db"
    backup_db(prefix)
