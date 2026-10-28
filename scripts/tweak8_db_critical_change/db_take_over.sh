#!/bin/sh
echo "Tweak8以前のDBをTweak8以降のものに変換します。"
echo "現在は古いmainにいる前提です。プロジェクトフォルダ（manage.pyと同じ）階層で実行してください。自動的に最新に更新します。（多分）"
echo "Ctrl+Cで中止、Enterを押して実行："
read _

set -e  # エラーが出たら即座に終了

echo "JSONへ書き出し、DBをバックアップと削除中："

mkdir -p fixtures
# ユーザー関連などのデータを全て除いて保存
echo "ユーザー関連データ以外を実行中"
python3 manage.py dumpdata \
    --natural-foreign \
    --natural-primary \
    --exclude=contenttypes \
    --exclude=main.youthsquaremap \
    --exclude=config.ec2operationslog \
    --exclude=auth.permission \
    --exclude=main.user \
    --exclude=main.user_friends \
    --exclude=main.user_groups \
    --exclude=main.user_user_permissions \
    --exclude=socialaccount.socialaccount \
    --exclude=socialaccount.socialapp \
    --exclude=socialaccount.socialapp_sites \
    --exclude=socialaccount.socialtoken \
    --exclude=django.admin_log \
    --exclude=account.emailaddress \
    --indent=2 \
    > fixtures/full_backup.json

echo "ユーザー関連データを実行中"
python3 manage.py dumpdata main.User -o fixtures/users.json
echo "変換中"
sed -i 's/main\.user/config.user/g' fixtures/users.json

#ここまで古い環境
echo "Gitでコードベースを更新中"
git fetch
git checkout main
git pull

echo "削除中"
python3 ./scripts/backup_db.py
rm ./db.sqlite3

echo "新しいDBの作成、データの読み込み中："
python3 manage.py makemigrations
python3 manage.py migrate
python3 manage.py loaddata fixtures/full_backup.json
python3 manage.py loaddata fixtures/users.json
python3 ./scripts/backup_db.py

echo "正常に全ての操作が完了しました。"
