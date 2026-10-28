"""
管理コマンド: GradeColor を学年分（中1〜高3）まとめて作成する。

使い方:
    python manage.py init_grade_colors
    python manage.py init_grade_colors --reset   # 既存レコードを削除して再生成
"""
from django.core.management.base import BaseCommand
from sports_fes.models import GradeColor


DEFAULTS = [
    (1, "e74c3c"),  # 中1
    (2, "e67e22"),  # 中2
    (3, "f1c40f"),  # 中3
    (4, "2ecc71"),  # 高1
    (5, "3498db"),  # 高2
    (6, "9b59b6"),  # 高3
]


class Command(BaseCommand):
    help = "GradeColor レコードを学年分まとめて生成します"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="既存のレコードをすべて削除してから再生成する",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            GradeColor.objects.all().delete()
            self.stdout.write("既存レコードを削除しました。")

        created, skipped = 0, 0
        for grade_num, color in DEFAULTS:
            obj, is_new = GradeColor.objects.get_or_create(
                grade_num=grade_num,
                defaults={"color": color},
            )
            if is_new:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"完了: {created} 件作成 / {skipped} 件スキップ（既存）"
            )
        )
