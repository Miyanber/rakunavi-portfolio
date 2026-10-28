"""
管理コマンド: SchoolClass を学年・クラス数の指定でまとめて生成する。

使い方:
    # 中1〜高3、各学年4クラスで一括生成
    python manage.py init_school_classes

    # 学年ごとにクラス数を指定
    python manage.py init_school_classes --counts 4 4 5 4 4 3
    #   → 中1:4, 中2:4, 中3:5, 高1:4, 高2:4, 高3:3

    # 既存レコードを削除して再生成
    python manage.py init_school_classes --counts 4 4 4 4 4 4 --reset
"""
from django.core.management.base import BaseCommand, CommandError
from sports_fes.models import SchoolClass

GRADE_LABELS = {1: "中1", 2: "中2", 3: "中3", 4: "高1", 5: "高2", 6: "高3"}


class Command(BaseCommand):
    help = "SchoolClass レコードを学年・クラス数の指定でまとめて生成します"

    def add_arguments(self, parser):
        parser.add_argument(
            "--counts",
            nargs=6,
            type=int,
            metavar=("中1", "中2", "中3", "高1", "高2", "高3"),
            default=[7, 7, 7, 9, 9, 9],
            help="各学年のクラス数を6つ指定（中1〜高3の順）",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="既存のレコードをすべて削除してから再生成する",
        )

    def handle(self, *args, **options):
        counts: list[int] = options["counts"]
        if any(c < 1 for c in counts):
            raise CommandError("クラス数は1以上で指定してください。")

        if options["reset"]:
            deleted, _ = SchoolClass.objects.all().delete()
            self.stdout.write(f"既存レコード {deleted} 件を削除しました。")

        created = skipped = 0
        for grade_num, class_count in enumerate(counts, start=1):
            for class_num in range(1, class_count + 1):
                _, is_new = SchoolClass.objects.get_or_create(
                    grade_num=grade_num,
                    class_num=class_num,
                )
                if is_new:
                    created += 1
                else:
                    skipped += 1
            self.stdout.write(
                f"  {GRADE_LABELS[grade_num]}: {class_count} クラス"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n正常に完了: {created} 件作成 / {skipped} 件スキップ（既存）\n"
                "応援団からクラスを割り当てて下さい。"
            )
        )
