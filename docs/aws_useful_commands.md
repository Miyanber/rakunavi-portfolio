# よく使うコマンド一覧

ほんとによく使います。特に Elastic IP の値や .pem ファイルに関しては開発中に値がコロコロ変わるものではないので、実際の値を代入したコマンドを `.env.development` 等にコメントアウトして保存しておくことをお勧めします。

## Linux 標準コマンド

### 管理者権限で実行

管理者権限は、主にインスタンス上で必要なことが多いです。`has no permission` みたいなエラーが出たら、`sudo` コマンドで実行してみましょう。

```bash
sudo <コマンド>
# 例: 管理者権限で .env ファイルを編集する
sudo nano .env
```

### ディレクトリを移動

```bash
cd <移動先ディレクトリ>
```

### ファイル一覧を取得

```bash
# 今いるディレクトリのファイル一覧を表示
ls 
# 隠しファイルも表示 (.env等)
ls -a
```

### ファイルを編集

```bash
nano <ファイル名>
```

### ファイルを開く

```bash
cat <ファイル名>
```

## インスタンス上で実行するコマンド

### インスタンスに SSH 接続する

```bash
# 一般形
ssh -i ~/.ssh/RakuNavi20XX.pem ubuntu@"Elastic IP アドレス"
# 例（宮崎の Windows WSL）
ssh -i ~/.ssh/RakuNavi2025.pem ubuntu@"203.0.113.10"
```

### RakuNavi リポジトリに移動する（ついでに仮想環境に入る）

```bash
cd ./RakuNavi
source .venv/bin/activate
```

### Django のログの確認

```bash
cat /var/log/rakunavi/django.log
```

#### Gunicorn のログの確認

```bash
# 直近50行のみ表示
sudo journalctl -u gunicorn.service -n 50
```

#### Nginx のログの確認

```bash
sudo journalctl -u nginx.service
```

#### Gunicorn, Nginx の再起動

```
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

## ローカルで実行するコマンド

### インスタンスにファイルをアップロードする

```bash
# ローカルのターミナルで実行
scp -i ~/.ssh/RakuNavi20XX.pem ENVファイルのパス ubuntu@"Elastic IP アドレス":~/RakuNavi/
# 例（らくなびリポジトリ直下に .env がある場合）
scp -i ~/.ssh/RakuNavi2025.pem .env ubuntu@"203.0.113.10":~/RakuNavi/
```