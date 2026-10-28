- [開発関連メモ](#開発関連メモ)
  - [iPad等で動作を確認したい](#ipad等で動作を確認したい)
  - [related\_nameを動的に設定したい](#related_nameを動的に設定したい)
  - [データベース共同開発の基本（重要）](#データベース共同開発の基本重要)
    - [fixture を作成して管理](#fixture-を作成して管理)
    - [主なコマンド](#主なコマンド)
      - [データベースの内容を全削除](#データベースの内容を全削除)
    - [注意](#注意)


# 開発関連メモ

## iPad等で動作を確認したい

[ngrok](https://ngrok.com/) を利用すると、ローカルで`runserver`したサーバーに外部からアクセスできるようになります。非常に便利ですので是非ご活用ください。

※学校のiPadから開く場合、初見のURLであるため一旦iFilterによる審査が入ります。1日程度待てば審査が通り、ページが開けるようになります。(2025年4月2日時点)

やり方は各自調べてください。なお、OSネイティブの機能を利用し、ローカルのサーバーをポート開放してiPadからアクセスしようとすると無理でした。恐らくiFilterが原因だと思われます。(2025年4月2日時点)

## related_nameを動的に設定したい

抽象クラスのモデルにおいて、
`related_name='%(class)s_profile'`を利用すると
related_name に子クラスの名前を利用できる。

## データベース共同開発の基本（重要）

### fixture を作成して管理

共同開発において、`db.sqlite3`を共同編集するとほぼ確実にコンフリクトが発生する。<br>
そのため、データベースを json 等のファイルに書き出して管理する必要がある。<br>
書き出した json 等のファイルのことを`fixture`と呼ぶ。<br>
**マイグレーションが異なるブランチに移動する際はfixtureを作成してから移動すると良い。**

### 主なコマンド

主なコマンドには以下のようなものがあります。

```bash
# fixtureの作成
python3 manage.py dumpdata <アプリ名>.<モデル名>(省略可) -o <出力先ファイル名>
# fixtureの読み込み
python3 manage.py loaddata <入力先ファイル名>
```

実際は以下のように使用することが多いです。`fixtures/` は `.gitignore` に指定されています。
```bash
# 全モデルの全オブジェクトを出力する
# fixture名は以下のように、日付とブランチが分かるようにするのがおすすめです。
python3 manage.py dumpdata -o fixtures/2025-04-02_optimizeDocuments.json --indent=4

# fixtureの読み込み
python3 manage.py loaddata fixtures/<fixture名>.json
```

※以下、コピペ用
```bash
python3 manage.py dumpdata -o fixtures/.json --indent=4

python3 manage.py loaddata fixtures/.json
```

#### データベースの内容を全削除
- 削除してよいデータであることを必ず確認すること！！
- マイグレーション履歴は変わらないので注意！
- マイグレーション履歴を消す場合は、`db.sqlite3`を削除する

```bash
python3 manage.py flush
```


### 注意
- きちんとマイグレートしてからデータを読み込むこと
- loaddata を使用した読み込みは、あくまでデータの追加・変更であり、データを全て置き換えるわけではない。元々あったデータは残る（はず）。
  -  全て置き換えたい場合は上述の`python manage.py flush`を実行してから loaddata を実行する。
- その他独自で初期化用の fixture ファイルを作成しても良い。

### TIPS
- pipの更新をしたい
らくなびでは、`requirements.in` で必要なパッケージを列挙し、` pip-compile requirements.in` を実行すれば一括で`requirements.txt` にそれらが依存するパッケージ全体を書き出されることで、`pip install -r requirements.txt` で依存関係をインストールできる仕組みになっています。
**一括更新をしたいなら、**
```bash
pip-compile --upgrade requirements.in
pip install -r requirements.txt
```

を実行すればいいです。 **`pip check`で依存関係パッケージが壊れていないかや、更新後正常に動作するか確認は必須です。**


### SSH接続できないトラブルシューティング
- 機能まではうまくSSH接続できたのに、なぜかできない、、？
Wifiルーターの再起動などでIPアドレスが変わることによって、セキュリティグループに定義されている許可リストから外れてしまうためです。

１   `curl https://ifconfig.me` で、PCのグローバルIPアドレスを確認
２   AWSにログイン、EC2＞セキュリティグループへ
３   「インバウンドのルールを編集」　タイプ：ssh　ソース：マイIP　ここにPCのIPアドレスを入力
４   EC2インスタンスを再起動
５   接続を試行！！

### ブラウザのコンソールでの「Loading the stylesheet '****.css' violates the following Content Security Policy directive:」エラー
読み込もうとしているCSSがCSPヘッダの設定に違反しいる、というエラーです。外部のスクリプトを読み込ませる際に起こったのではないでしょうか。
そもそもCSPとは、XSS攻撃を防ぐための手法で、スクリプトのURLを検証し、許可されているものだけ実行させることで、攻撃者によってHTMLに不正なコードが注入され、悪意があるスクリプトを読み込まれようとしても（悪意のあるスクリプトのURLはCSPに登録されていないため）ブロックできるというものです。
→これを解決するには、`settings.py` のSECURE\_CSP内の該当箇所（JSなら"script-src", CSSなら"style-src"）にドメインを追加します。
SECURE_CSPはポリシー違反があった場合警告を発し実行のブロックを行います。CSP自体はかなり高度なセキュリティ設定なので、上手くできなければ最悪SECURE_CSP_REPORT_ONLYに書き換えても構いません。こちらでは、違反の場合に警告のみを発します。

