- [カスタムコマンド一覧](#カスタムコマンド一覧)
  - [`export_handouts_test` コマンド](#export_handouts_test-コマンド)
    - [説明](#説明)
      - [注意事項](#注意事項)
    - [使い方](#使い方)
    - [引数](#引数)
      - [必須](#必須)
      - [オプション（省略可）](#オプション省略可)
    - [結果](#結果)
    - [利用例](#利用例)

# カスタムコマンド一覧

らくなびでは、様々な作業を効率的に行う為、独自コマンドを実装しているものがあります。説明なんていいから早く使わせてくれよという場合は、各コマンドの「利用例」の項目を参考にして下さい。

## `export_handouts_test` コマンド

### 説明

展示担当者・野外ライブ出場者・音楽室ライブ出場者向けに、紹介入力フォームのQRコードを記載した配布資料のPDF（以下、「配布プリント」）をテスト出力します。
マイページの「説明会資料 PDF のダウンロード」機能のテスト用です。


※テスト出力のため、データの作成等は実際には行われません。

#### 注意事項

- **PDF出力には 1 ページ当たり 5 秒程かかります。ご了承下さい。**
- **Windowsの場合、[GTK for Windows Runtime Environment](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer?tab=readme-ov-file) というやつが必要らしいです。その他のOSでも追加でパッケージが必要な場合がありますので、その場合は適宜インストールしてください。**

### 使い方

```bash
python manage.py export_handouts_test <出力対象> --output-dir <出力先ディレクトリ（省略可）>
```

### 引数

#### 必須
- **出力対象**：野外ライブ（live_stage_performance）, 音楽室ライブ（music_room_performance）, 展示（exhibition） のいずれかを指定。

#### オプション（省略可）
- `--output-dir` 出力先ディレクトリ：出力先ディレクトリを指定。デフォルトは`handouts/出力対象/現在日時/`。

### 結果

ディレクトリ（デフォルトでは`handouts/出力対象/現在日時/`）に配布プリントのPDFが出力されます。

ディレクトリの`single/`内には、各展示・ライブの個別のPDFが出力されます。ディレクトリ直下には、それらを1ファイルにまとめたPDF（XXX用配布プリント.pdf）が出力されます。

ログで出力されるパスは、`Ctrl`を押しながらクリック（Windowsの場合）するとVSCode上でPDFを開く事ができます。※VSCode上でPDFをプレビューするには拡張機能が必要です。

### 利用例

1. 野外ライブ向けの配布プリントをテスト作成したい。
   ```bash
    python manage.py export_handouts live_stage_performance
    # handouts/live_stage_performance/ に出力
   ```
2. 展示向けの配布プリントをテスト作成したい。
   ```bash
    python manage.py export_handouts exhibition
    # handouts/exhibition/ に出力
   ```