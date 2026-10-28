- [エラー解決用備忘録](#エラー解決用備忘録)
  - [Is the docker daemon running? と言われたとき](#is-the-docker-daemon-running-と言われたとき)
  - ['That port is already in use.' エラーが出るとき](#that-port-is-already-in-use-エラーが出るとき)
  - [環境変数が.env 通りにならないとき](#環境変数がenv-通りにならないとき)
  - [migrate ができないとき](#migrate-ができないとき)
  - [永遠に CSS の更新が反映されないとき](#永遠に-css-の更新が反映されないとき)
  - [django-allauth でマイクレーションができないとき](#django-allauth-でマイクレーションができないとき)
  - [★fixtureをロードできないとき](#fixtureをロードできないとき)
    - [django.db.utils.IntegrityError: Could not load XXX: UNIQUE constraint failed: XXX.content\_type\_id, XXX.codename](#djangodbutilsintegrityerror-could-not-load-xxx-unique-constraint-failed-xxxcontent_type_id-xxxcodename)
    - [上の方法でも直らないよーって時](#上の方法でも直らないよーって時)

# エラー解決用備忘録

## Is the docker daemon running? と言われたとき

```bash
# dockerデーモン起動
$ sudo service docker start

# dockerデーモンステータス確認
$ sudo service docker status

# dockerデーモン停止
$ sudo service docker stop
```

## 'That port is already in use.' エラーが出るとき
前回の`runserver`時にプロセスを終了しないままターミナルを閉じてしまったことが原因です。プロセスを終了すれば解決します。

```bash
# 現在のプロセスを表示
lsof -i:8000
# PIDを指定してプロセス終了
kill <PID>
# PIDを指定してプロセス終了(強制)
kill -9 <PID>
```

## 環境変数が.env 通りにならないとき

Django の設定では、環境変数や.env ファイル、settings.py ファイル内で設定された順序が影響する場合があります。環境変数が優先されている可能性があるため、システム環境変数を確認し、DEBUG がどのように設定されているか確認してください。

※現在はpython-dotenvモジュールにて、読み込み時に`override=True`オプションを利用しているので大丈夫かと思われます。

```bash
# 以下のコマンドを実行して、環境変数にDEBUGが設定されていないか確認します。
echo $DEBUG
# もしTrueが返される場合は、環境変数が上書きされています。設定を解除するか、正しい値に設定してください。
unset DEBUG  # もしくは export DEBUG=False
```

## migrate ができないとき

django-allauthにて不具合が発生する場合があるようです。
```bash
# 以下をエラー後実行（エラー前の方が良い？）
python3 manage.py migrate account 0006 --fake
```

## 永遠に CSS の更新が反映されないとき

環境変数で`DEBUG=True`になっていることを確認する。

## django-allauth でマイクレーションができないとき

エラー内容：`Cannot resolve keyword 'email' into field.`

解決方法：マイグレーションファイル`0006_emailaddress_lower.py`の E メール関連をコメントアウトして保存し、再マイグレーションしてまた戻す。

## ★fixtureをロードできないとき

### django.db.utils.IntegrityError: Could not load XXX: UNIQUE constraint failed: XXX.content_type_id, XXX.codename

content_type絡みのエラーです。なんかシランケドよく出てきます。対処法は以下の通りです。

```bash
python manage.py loaddata fixtures/XXX.json --exclude=contenttypes
```

上のコマンドのように、`--exclude=contenttypes`を末尾に追加して、contenttypeの出力/入力を無くせばOKです。

また、一応fixtureを直接開いてcontenttypeのところを消すとかでもOKです。**`dumpdata`の際にもこのオプションを使っておくと、予期せぬエラーを防ぐことができるかもしれません。**

### 上の方法でも直らないよーって時

仕方がないので、fixtureファイルを直接開いて、エラーが出ているモデルのオブジェクトを削除して下さい。特に、`contenttypes.contenttype`や`auth.permission`等のモデルは消しても問題ないことがほとんどです。