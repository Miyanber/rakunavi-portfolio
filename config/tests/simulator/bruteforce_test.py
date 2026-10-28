"""
RakuNavi トークン ブルートフォース実打テスト
============================================

使い方:
    # Django環境をセットアップしてから実行
    python bruteforce_test.py [--attempts N] [--model exhibition|performance|food_booth|all]
                              [--base-url http://127.0.0.1:8000]

概要:
    secrets.token_urlsafe(64) で生成した512ビットのランダムトークンを
    runserver中のサーバー（デフォルト: http://127.0.0.1:8000）に実際にHTTPリクエストで送信する。

    トークンはビューの認証フローに合わせて ?token=<値> クエリパラメータで送る。
    （UseTokenMixin が GET パラメータでセッションにセットする仕組みを利用）

    もし 200 が返ってきた（= 偶然ヒット）場合は AssertionError を raise して即終了する。

注意:
    - python manage.py runserver が起動していること
    - DBに対象オブジェクトが1件以上存在すること
    - requestsライブラリが必要: pip install requests
"""

import argparse
import os
import sys
import math
import secrets
import time

import django

# ============================================================
# Django セットアップ（manage.py と同じディレクトリから実行する想定）
# ============================================================
# このファイルがどこに置かれていても manage.py のある
# プロジェクトルートを自動で探して sys.path に追加する
def _find_project_root() -> str:
    """manage.py が存在するディレクトリをプロジェクトルートとして返す"""
    here = os.path.abspath(__file__)
    current = os.path.dirname(here)
    while True:
        if os.path.exists(os.path.join(current, "manage.py")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            raise FileNotFoundError(
                "manage.py が見つかりません。"
                "プロジェクトルート以下にこのスクリプトを配置してください。"
            )
        current = parent

project_root = _find_project_root()
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rakunavi.settings")
django.setup()

# django.setup() 後にインポート
from django.urls import reverse
from main.models import Exhibition, Performance, FoodBooth

try:
    import requests
except ImportError:
    print("ERROR: requests がインストールされていません。")
    print("       pip install requests  を実行してください。")
    sys.exit(1)


# ============================================================
# 攻撃対象の収集
# ============================================================

def get_targets(model_filter: str, base_url: str) -> list[dict]:
    """
    DBから全オブジェクトを取得し、攻撃対象リストを返す。

    トークン認証の仕組み（UseTokenMixin / views.py）:
        GET ?token=<値> → session["edit_token"] にセット
        → ビューの test_func() で session["edit_token"] == object.token を比較
    
    よって URL は  /detail/<pk>/?token=<fake>  の形で叩く。
    """
    targets = []

    if model_filter in ("exhibition", "all"):
        for ex in Exhibition.objects.all():
            path = reverse("main:exhibition_detail", kwargs={"pk": ex.pk})
            targets.append({
                "model":       "exhibition",
                "label":       "展示",
                "pk":          ex.pk,
                "name":        str(ex),
                "path":        path,
                "full_url":    base_url + path,
                "real_token":  str(ex.token),
            })

    if model_filter in ("performance", "all"):
        for perf in Performance.objects.all():
            path = reverse("main:performance_detail", kwargs={"pk": perf.pk})
            targets.append({
                "model":       "performance",
                "label":       "ライブ",
                "pk":          perf.pk,
                "name":        str(perf),
                "path":        path,
                "full_url":    base_url + path,
                "real_token":  str(perf.token),
            })

    if model_filter in ("food_booth", "all"):
        for fb in FoodBooth.objects.all():
            path = reverse("main:food_booth_detail", kwargs={"pk": fb.pk})
            targets.append({
                "model":       "food_booth",
                "label":       "模擬店",
                "pk":          fb.pk,
                "name":        str(fb),
                "path":        path,
                "full_url":    base_url + path,
                "real_token":  str(fb.token),
            })

    return targets


# ============================================================
# 接続確認
# ============================================================

def check_server(base_url: str) -> None:
    """サーバーが起動しているか確認する"""
    try:
        r = requests.get(base_url, timeout=5)
        print(f"  サーバー確認: {base_url} → HTTP {r.status_code} ✅")
    except requests.exceptions.ConnectionError:
        print(f"\nERROR: {base_url} に接続できません。")
        print("       python manage.py runserver が起動しているか確認してください。")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print(f"\nERROR: {base_url} への接続がタイムアウトしました。")
        sys.exit(1)


# ============================================================
# 1回の攻撃試行
# ============================================================

def attack_once(session: requests.Session, target: dict) -> dict:
    """
    512ビットのランダムトークンを生成し、対象URLに GET リクエストを送る。

    UseTokenMixin の dispatch() が  ?token=<値>  を session にセットするので、
    クエリパラメータとして渡す。requests.Session でクッキー（セッション）を維持する。

    Returns:
        hit         : fake_token が real_token と完全一致して 200 が返った場合 True
        open_access : fake_token は不一致だが 200 が返った場合 True（permission緩い）
        status      : HTTPステータスコード
        token       : 生成したランダムトークン
    """
    fake_token = secrets.token_urlsafe(64)
    url = target["full_url"]

    try:
        response = session.get(
            url,
            params={"token": fake_token},
            timeout=10,
            allow_redirects=True,
        )
    except requests.exceptions.RequestException as e:
        return {
            "token":        fake_token,
            "status":       -1,
            "hit":          False,
            "open_access":  False,
            "error":        str(e),
        }

    status = response.status_code
    # トークンが偶然一致して認証が通った場合
    is_hit = (status == 200 and fake_token == target["real_token"])
    # status==200 かつトークン不一致 → 正当な理由で公開されている
    # （display_introduction==True による一般公開、またはスーパーユーザー）
    # これはトークン認証を突破したわけではなく正常な動作
    is_open = (status == 200 and fake_token != target["real_token"])

    return {
        "token":        fake_token,
        "status":       status,
        "hit":          is_hit,
        "open_access":  is_open,
        "error":        None,
    }


# ============================================================
# メイン処理
# ============================================================

SEP = "=" * 60

def main():
    parser = argparse.ArgumentParser(
        description="RakuNavi トークン ブルートフォース実打テスト"
    )
    parser.add_argument(
        "--attempts", "-n",
        type=int, default=1000,
        help="1オブジェクトあたりの試行回数（デフォルト: 1000）",
    )
    parser.add_argument(
        "--model", "-m",
        type=str, default="all",
        choices=["exhibition", "performance", "food_booth", "all"],
        help="攻撃対象モデル（デフォルト: all）",
    )
    parser.add_argument(
        "--base-url", "-u",
        type=str, default="http://127.0.0.1:8000",
        help="runserver のベースURL（デフォルト: http://127.0.0.1:8000）",
    )
    parser.add_argument(
        "--stop-on-open-access",
        action="store_true", default=False,
        help="一般公開中（display_introduction=True）でランダムトークンでも 200 が返る場合もエラー終了する（公開前のテスト用）",
    )
    args = parser.parse_args()

    base_url    = args.base_url.rstrip("/")
    attempts    = args.attempts
    model_filter= args.model
    stop_on_open= args.stop_on_open_access

    print(f"\n{SEP}")
    print(" RakuNavi ブルートフォース実打テスト")
    print(f" 実行日時: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(SEP)

    # サーバー疎通確認
    print("\n[1] サーバー疎通確認...")
    check_server(base_url)

    # 攻撃対象収集
    print("\n[2] 攻撃対象を収集中...")
    targets = get_targets(model_filter, base_url)
    if not targets:
        print(f"ERROR: 対象オブジェクトが見つかりません（model={model_filter}）")
        print("       DBにデータが存在するか確認してください。")
        sys.exit(1)

    print(f"  対象: {len(targets)} 件 × {attempts} 試行 = 合計 {len(targets) * attempts:,} リクエスト")
    for t in targets:
        print(f"    [{t['label']}] pk={t['pk']}  {t['name'][:40]}")

    print(f"\n[3] 攻撃開始 → {base_url}")
    print(SEP)

    # requests.Session でクッキーを維持（セッション認証のため）
    http = requests.Session()

    total_tried     = 0
    total_hits      = 0
    total_open      = 0
    total_errors    = 0
    start           = time.perf_counter()

    for target in targets:
        print(f"\n  [{target['label']}] {target['name'][:50]} (pk={target['pk']})")
        print(f"  URL: {target['full_url']}")

        hits_here  = 0
        open_here  = 0
        err_here   = 0

        for i in range(attempts):
            result = attack_once(http, target)
            total_tried += 1

            # ── 通信エラー ──
            if result["error"]:
                total_errors += 1
                err_here += 1
                if err_here == 1:
                    print(f"\n  [通信エラー] {result['error']}")
                continue

            # ── 進捗（100回ごとに上書き表示）──
            if (i + 1) % 100 == 0:
                elapsed = time.perf_counter() - start
                rps = total_tried / elapsed if elapsed > 0 else 0
                print(
                    f"  {i+1:>6}/{attempts}  "
                    f"status={result['status']}  "
                    f"速度={rps:.0f} req/s  "
                    f"hits={hits_here}",
                    end="\r", flush=True
                )

            # ── ヒット検出（最重要）──
            if result["hit"]:
                total_hits += 1
                hits_here  += 1
                # 即座にエラーを出して終了
                print()  # 進捗行を改行
                raise AssertionError(
                    "\n"
                    + "!" * 60 + "\n"
                    "  ブルートフォース成功: トークンが一致しました！\n"
                    + "!" * 60 + "\n"
                    f"  モデル    : {target['model']}\n"
                    f"  オブジェクト: {target['name']}\n"
                    f"  pk        : {target['pk']}\n"
                    f"  試行回数  : {total_tried:,}\n"
                    f"  一致token : {result['token']}\n"
                    f"  URL       : {target['full_url']}\n"
                    "\n  → generate_secure_token() の実装を見直してください。\n"
                )

            # ── オープンアクセス検出 ──
            if result["open_access"]:
                total_open += 1
                open_here  += 1
                if open_here == 1:
                    print(f"\n  [情報] ランダムトークンでも 200 が返っています (pk={target['pk']})")
                    print( "         → display_introduction=True による一般公開中、またはスーパーユーザーでのアクセスです。")
                    print( "         → トークン認証を突破したわけではありません（正常な動作）。")
                if stop_on_open:
                    raise AssertionError(
                        "一般公開検出（--stop-on-open-access）\n"
                        f"  URL: {target['full_url']}\n"
                        "  display_introduction=True で一般公開中のため、トークンなしでも閲覧できます。\n"
                        "  公開前の状態でテストしたい場合は permission.display_introduction を False にしてください。"
                    )

        print()  # 進捗行の改行
        status_str = "✅ ヒットなし" if hits_here == 0 else f"❌ ヒット {hits_here} 件"
        print(f"  完了: {attempts} 試行  {status_str}  open={open_here}  errors={err_here}")

    # ── 最終サマリー ──
    elapsed = time.perf_counter() - start
    rps = total_tried / elapsed if elapsed > 0 else 0

    print(f"\n{SEP}")
    print(" 結果サマリー")
    print(SEP)
    print(f"  総試行数          : {total_tried:,}")
    print(f"  実行時間          : {elapsed:.2f} 秒")
    print(f"  実効速度          : {rps:.1f} req/sec")
    print(f"  トークンヒット数  : {total_hits}  ← これが 0 以外なら重大インシデント")
    print(f"  一般公開アクセス  : {total_open} 件（display_introduction=True による正常な公開）")
    print(f"  通信エラー        : {total_errors} 件")

    if total_hits == 0:
        print(f"\n  ✅ ブルートフォース耐性: 問題なし")
        print(f"     {total_tried:,} 回試行してトークンの一致は 0 件でした。")
        print(f"     トークン空間: 2^512 ≈ 10^154 通り")
    else:
        raise AssertionError(f"トークンヒット {total_hits} 件。セキュリティを確認してください。")

    print()


if __name__ == "__main__":
    main()
