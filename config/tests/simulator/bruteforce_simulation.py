"""
RakuNavi トークン ブルートフォース耐性シミュレーター
=====================================================

目的:
    展示 / ライブ / 模擬店 の編集トークン（secrets.token_urlsafe(64) 生成）に対して
    ブルートフォース攻撃がどのくらいの時間・試行回数を必要とするかを定量的に示す。

実行方法:
    python bruteforce_simulation.py [--requests-per-sec N] [--targets N]

注意:
    このスクリプトは実際のネットワーク通信を一切行いません。
    数学的なシミュレーションのみです。自分のサービスの安全性を確認するためだけに使用してください。
"""

import argparse
import math
import secrets
import time
from dataclasses import dataclass, field
from typing import Literal

# ============================================================
# トークンの仕様
# ============================================================
# secrets.token_urlsafe(64) の仕様:
#   - 64バイト(512ビット)のランダム性
#   - Base64url エンコード後 → 約86文字
#   - 使用文字: A-Z a-z 0-9 - _ (64種)
#   - エントロピー: 512 ビット

TOKEN_ENTROPY_BITS = 512          # secrets.token_urlsafe(64) のランダム性
TOKEN_CHARSET_SIZE = 64           # url-safe base64 の文字種数
TOKEN_LENGTH = 86                 # 生成されるトークンの文字数（概算）
KEYSPACE = 2 ** TOKEN_ENTROPY_BITS  # 総トークン空間

ModelName = Literal["exhibition", "performance", "food_booth"]


# ============================================================
# データクラス
# ============================================================

@dataclass
class AttackConfig:
    """攻撃シナリオの設定"""
    model: ModelName
    label: str
    # 攻撃者が1秒間に送れるリクエスト数（現実的な上限を想定）
    requests_per_sec: int = 1_000
    # 攻撃対象のトークン数（DBに存在するオブジェクト数）
    num_targets: int = 30

@dataclass
class AttackResult:
    """シミュレーション結果"""
    config: AttackConfig
    keyspace: int
    entropy_bits: int
    # 確率 p で1つ当てるのに必要な試行回数
    trials_for_50pct: int   # 50% の確率で1トークンを当てる試行数
    trials_for_1pct: int    # 1% の確率
    # 時間換算
    seconds_for_50pct: float
    seconds_for_1pct: float
    # 実測: N件のトークンを生成して重複チェック
    collision_in_sample: bool
    sample_size: int


# ============================================================
# 計算ロジック
# ============================================================

def trials_needed(probability: float, keyspace: int, num_targets: int) -> int:
    """
    keyspace 個のトークン空間で num_targets 個の有効トークンが存在するとき、
    ランダム試行で確率 probability 以上でヒットするのに必要な試行回数を返す。

    誕生日問題的アプローチ:
        P(ヒットなし, n回) = ((keyspace - num_targets) / keyspace)^n
        P(1回以上ヒット) = 1 - P(ヒットなし) >= probability
        n >= log(1 - probability) / log(1 - num_targets/keyspace)
    """
    # keyspace が 2^512 と巨大なため float では hit_prob_per_trial ≈ 0 になり
    # 通常の除算が使えない。対数近似式を使う:
    #   n ≈ -log(1 - probability) / (num_targets / keyspace)
    #     = -log(1 - probability) * keyspace / num_targets
    # さらに keyspace が Python int なので Decimal で高精度計算する。
    from decimal import Decimal, getcontext
    getcontext().prec = 60
    log_p = Decimal(str(math.log(1 - probability)))  # 負の値
    # n ≈ -log(1-p) * keyspace / num_targets
    n_decimal = (-log_p) * Decimal(keyspace) / Decimal(num_targets)
    return int(n_decimal.to_integral_value()) + 1


def seconds_to_human(seconds: float) -> str:
    """秒数を人間が読みやすい形式に変換（超大数対応）"""
    years = seconds / (86400 * 365)
    if years >= 1:
        exp = math.floor(math.log10(years))
        if exp >= 6:
            return f"約 10^{exp:.0f} 年"
        return f"{years:,.0f} 年"
    days = seconds / 86400
    if days >= 1:
        return f"{days:,.1f} 日"
    hours = seconds / 3600
    if hours >= 1:
        return f"{hours:,.1f} 時間"
    minutes = seconds / 60
    if minutes >= 1:
        return f"{minutes:,.1f} 分"
    return f"{seconds:.2f} 秒"


def format_large_number(n: int) -> str:
    """大きな整数を指数表記で返す"""
    if n < 1_000_000:
        return f"{n:,}"
    exp = math.floor(math.log10(n))
    coef = n / (10 ** exp)
    return f"{coef:.2f} × 10^{exp}"


def collision_check(sample_size: int) -> bool:
    """sample_size 個のトークンを実際に生成して衝突を確認"""
    tokens = [secrets.token_urlsafe(64) for _ in range(sample_size)]
    return len(tokens) != len(set(tokens))


# ============================================================
# シミュレーション実行
# ============================================================

def simulate(config: AttackConfig) -> AttackResult:
    t50 = trials_needed(0.50, KEYSPACE, config.num_targets)
    t1  = trials_needed(0.01, KEYSPACE, config.num_targets)
    return AttackResult(
        config=config,
        keyspace=KEYSPACE,
        entropy_bits=TOKEN_ENTROPY_BITS,
        trials_for_50pct=t50,
        trials_for_1pct=t1,
        seconds_for_50pct=t50 / config.requests_per_sec,
        seconds_for_1pct=t1 / config.requests_per_sec,
        collision_in_sample=collision_check(100_000),
        sample_size=100_000,
    )


# ============================================================
# レポート表示
# ============================================================

SEPARATOR = "=" * 72

def print_report(result: AttackResult) -> None:
    c = result.config
    print(SEPARATOR)
    print(f"  対象モデル : {c.label}  ({c.model})")
    print(f"  攻撃速度   : {c.requests_per_sec:,} req/sec")
    print(f"  有効トークン数 : {c.num_targets} 件（DBに存在するオブジェクト数）")
    print(SEPARATOR)

    print(f"\n【トークン空間】")
    print(f"  エントロピー     : {result.entropy_bits} ビット")
    print(f"  総トークン数     : {format_large_number(result.keyspace)}")
    print(f"  (参考) 宇宙の原子数 ≈ 10^80, このトークン空間 ≈ 10^{math.log10(result.keyspace):.0f}")

    print(f"\n【ブルートフォース所要試行数】")
    print(f"  1% の確率で1つ当てる  : {format_large_number(result.trials_for_1pct)} 回")
    print(f"  50%の確率で1つ当てる  : {format_large_number(result.trials_for_50pct)} 回")

    print(f"\n【所要時間（{c.requests_per_sec:,} req/sec の攻撃者）】")
    print(f"  1% の確率で成功するまで  : {seconds_to_human(result.seconds_for_1pct)}")
    print(f"  50%の確率で成功するまで  : {seconds_to_human(result.seconds_for_50pct)}")

    print(f"\n【実測: {result.sample_size:,} 件生成して衝突チェック】")
    status = "衝突あり ⚠️" if result.collision_in_sample else "衝突なし ✅"
    print(f"  結果: {status}")

    print(f"\n【結論】")
    years_50 = result.seconds_for_50pct / (86400 * 365)
    if years_50 > 1e10:
        safety = "🔒 極めて安全（宇宙の年齢を超える時間が必要）"
    elif years_50 > 1e6:
        safety = "🔒 非常に安全"
    elif years_50 > 1000:
        safety = "✅ 安全"
    else:
        safety = "⚠️  要注意"
    print(f"  {safety}")
    print()


def print_comparison_table(results: list[AttackResult]) -> None:
    """3モデルの比較サマリーテーブル"""
    print("\n" + SEPARATOR)
    print("  比較サマリー")
    print(SEPARATOR)
    header = f"{'モデル':<12} {'速度(req/s)':<14} {'50%成功までの年数':>20}"
    print(header)
    print("-" * 50)
    for r in results:
        years = r.seconds_for_50pct / (86400 * 365)
        years_str = f"10^{math.log10(years):.0f}" if years > 1e6 else f"{years:,.0f}"
        print(f"{r.config.label:<12} {r.config.requests_per_sec:<14,} {years_str:>20}")
    print()


def print_rate_limit_advice() -> None:
    """レートリミット導入による効果の試算"""
    print(SEPARATOR)
    print("  レートリミット導入による効果（参考）")
    print(SEPARATOR)
    scenarios = [
        ("制限なし（現状）",    1_000),
        ("IP毎 60req/min",      1),
        ("IP毎 10req/min",      0.167),
        ("IP毎  1req/min",      0.017),
    ]
    print(f"{'シナリオ':<24} {'実効速度':<14} {'50%成功まで'}")
    print("-" * 60)
    for label, rps in scenarios:
        t50 = trials_needed(0.50, KEYSPACE, 30)
        secs = t50 / rps
        years = secs / (86400 * 365)
        exp = math.floor(math.log10(years)) if years > 0 else 0
        print(f"{label:<24} {rps:<14.3f} 10^{exp:.0f} 年")
    print()


# ============================================================
# エントリーポイント
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="RakuNavi トークン ブルートフォース耐性シミュレーター"
    )
    parser.add_argument(
        "--requests-per-sec", "-r",
        type=int,
        default=1_000,
        help="攻撃者が1秒間に送れるリクエスト数（デフォルト: 1000）",
    )
    parser.add_argument(
        "--targets", "-t",
        type=int,
        default=30,
        help="DBに存在する有効トークン数（デフォルト: 30）",
    )
    args = parser.parse_args()

    configs = [
        AttackConfig("exhibition",   "展示",   args.requests_per_sec, args.targets),
        AttackConfig("performance",  "ライブ", args.requests_per_sec, args.targets),
        AttackConfig("food_booth",   "模擬店", args.requests_per_sec, args.targets),
    ]

    print(f"\n{'=' * 72}")
    print("  RakuNavi トークン ブルートフォース耐性シミュレーター")
    print(f"  実行日時: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 72}\n")

    results = []
    for config in configs:
        print(f"  [{config.label}] シミュレーション中...")
        result = simulate(config)
        results.append(result)
        print_report(result)

    print_comparison_table(results)
    print_rate_limit_advice()

    print(SEPARATOR)
    print("  補足: このスクリプトは数学的シミュレーションのみです。")
    print("  実際のネットワーク通信は一切行っていません。")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
