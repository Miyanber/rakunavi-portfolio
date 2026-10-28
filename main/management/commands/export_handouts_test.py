from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from main.models import Performance, Spot, Exhibition, FoodBooth, ExhibitionCategory
from rakunavi.utils import generate_qr_base64, sanitize_filename
from django.urls import reverse_lazy

import os
from datetime import datetime


class Command(BaseCommand):
    help = '指定したモデルの空オブジェクトを作成し、それぞれの編集用ページのQRコードを記載した配布プリントPDFを出力するコマンド'

    DEFAULT_LIVE_STAGE_COUNT = 15
    DEFAULT_MUSIC_ROOM_COUNT = 5
    DEFAULT_EXHIBITION_XLSX_PATH = "docs/展示一覧表.xlsx"

    def add_arguments(self, parser) -> None:
        parser.add_argument('model', type=str, choices=["live_stage_performance", "music_room_performance", "exhibition", "food_booth"], help='出力するモデルを指定。野外ライブ（live_stage_performance）, 音楽室ライブ（music_room_performance）, 展示（exhibition）, 模擬店（food_booth） のいずれか。')
        parser.add_argument('--output-dir', type=str, help='出力先ディレクトリを指定。デフォルトは"handouts/モデル/現在日時/"。')

    def handle(self, *args, **options) -> None:
        model = options['model']
        if model not in ['live_stage_performance', 'music_room_performance', 'exhibition', 'food_booth']:
            self.stdout.write(self.style.ERROR("モデル名は [live_stage_performance, music_room_performance, exhibition, food_booth] のいずれかを指定してください。"))
            exit(1)
        
        datestr = "20250901"
        if not datestr:
            self.stdout.write(self.style.ERROR("プリントを配布する日付をYYYYMMDD形式で指定してください。"))
            exit(1)
        try: 
            self.date = datetime.strptime(datestr, "%Y%m%d").date()
        except ValueError:
            self.stdout.write(self.style.ERROR("プリントを配布する日付の形式が不正です。YYYYMMDD形式で指定してください。"))
            exit(1)
        
        deadline_str = "202509252359"
        deadline = datetime.strptime(deadline_str, "%Y%m%d%H%M")
        days = ["月", "火", "水", "木", "金", "土", "日"]
        self.deadline = f"{deadline.month}月{deadline.day}日({days[deadline.weekday()]}) {deadline.hour}時"
        if deadline.minute > 0:
            self.deadline += f"{deadline.minute}分"

        
        if options.get("output-dir"):
            self.output_dir = options['output-dir']
        else:
            self.output_dir = os.path.join("handouts", model)
        os.makedirs(self.output_dir, exist_ok=True) # 出力先ディレクトリが存在しない場合は作成
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if model == "live_stage_performance":
            output_path = self.export_live_stage_performance()
        elif model == "music_room_performance":
            output_path = self.export_music_room_performance()
        elif model == "exhibition":
            output_path = self.export_exhibition()
        elif model == "food_booth":
            output_path = self.export_food_booth()
            
        self.stdout.write(self.style.SUCCESS(f"配布プリントPDF作成完了: {output_path}"))
    
    def export_performance(self, spot: Spot, count: int, template: str, file_name: str) -> str:        
        performances: list[Performance] = []
        performances.append(Performance(pk=1, spot=spot))
        
        context = {
            "date": self.date,
            "deadline": self.deadline,
            "objects": [],
        }
        
        for performance in performances:
            context["objects"].append({
                "id": performance.id,
                "spot": spot,
                "qr": generate_qr_base64(reverse_lazy("main:performance_edit", kwargs={"pk": performance.pk}) + f'?token={performance.token}'),
            })
        
        html_string = render_to_string(template, context)
        pdf_path = os.path.join(self.output_dir, sanitize_filename(file_name))
        self.stdout.write(f"配布プリントPDF出力中: {pdf_path}")
        
        convert_to_pdf(html_string, pdf_path)
        
        return pdf_path
    
    def export_live_stage_performance(self) -> str:
        live_stage = Spot.objects.get(name="野外ライブステージ")
        count = self.DEFAULT_LIVE_STAGE_COUNT
        return self.export_performance(live_stage, count, "main/export/handout/performance.html", f"野外ライブ用配布プリントB5_{self.timestamp}.pdf")

    def export_music_room_performance(self) -> str:
        music_room = Spot.objects.get(name="音楽室")
        count = self.DEFAULT_MUSIC_ROOM_COUNT
        return self.export_performance(music_room, count, "main/export/handout/performance.html", f"音楽室ライブ用配布プリントB5_{self.timestamp}.pdf")

    def export_exhibition(self) -> str:
        exhibitions: list[Exhibition] = []
        exhibitions.append(Exhibition(pk=1, grade_number=1, class_number=1, title="クラス展示名が入ります", category=ExhibitionCategory.CLASS))
        exhibitions.append(Exhibition(pk=2, title="クラブ展示名が入ります", category=ExhibitionCategory.CLUB))

        context = {
            "date": self.date,
            "deadline": self.deadline,
            "objects": [],
        }
        
        for exhibition in exhibitions:
            exhibition_dict = {
                "id": exhibition.pk,
                "title": exhibition.title,
                "category": exhibition.category,
                "grade_number": exhibition.grade_number,
                "class_number": exhibition.class_number,
                "qr_exhibition": generate_qr_base64(reverse_lazy("main:exhibition_edit", kwargs={"pk": exhibition.pk}) + f'?token={exhibition.token}'),
                "qr_attraction": generate_qr_base64(reverse_lazy("main:attraction_create", kwargs={"pk": exhibition.pk}) + f'?token={exhibition.token}'),
            }
            context["objects"].append(exhibition_dict)

        html_string = render_to_string("main/export/handout/exhibition.html", context)
        pdf_path = os.path.join(self.output_dir, f"展示用配布プリントA4_{self.timestamp}.pdf")
        self.stdout.write(f"配布プリントPDF出力中: {pdf_path}")
        
        convert_to_pdf(html_string, pdf_path)
    
        return pdf_path
    
    def export_food_booth(self) -> str:
        context = {
            "date": self.date,
            "deadline": self.deadline,
            "objects": [],
        }
        
        for food_booth in [FoodBooth(pk=1, name="模擬店名が入ります", grade_number=1, class_number=1)]:
            food_booth_dict = {
                "id": food_booth.pk,
                "name": food_booth.name,
                "grade_number": food_booth.grade_number,
                "class_number": food_booth.class_number,
                "qr": generate_qr_base64(reverse_lazy("main:food_booth_edit", kwargs={"pk": food_booth.pk}) + f'?token={food_booth.token}'),
            }
            context["objects"].append(food_booth_dict)
        
        html_string = render_to_string("main/export/handout/food_booth.html", context)
        pdf_path = os.path.join(self.output_dir, f"模擬店用配布プリントA4_{self.timestamp}.pdf")
        
        convert_to_pdf(html_string, pdf_path)

        return pdf_path
    

def convert_to_pdf(html_string, output_path) -> None:
    """
    HTML文字列からPDFを生成する。
    Weasyprintと依存関係にあるライブラリをインストールしなくても、
    PDF生成以外の機能は使えるようにするため、関数に処置を分けている。
    """
    try:
        from weasyprint import HTML
    except OSError:
        raise RuntimeError('Weasyprintに必要なライブラリがインストールされていません。エラーログの前に記載されているリンク ("WeasyPrint could not import some external libraries." の下部に記載あり) を参考に、OSに応じて必要なライブラリをインストールしてください。')
    
    HTML(string=html_string).write_pdf(output_path)