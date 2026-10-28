# スクリプトドキュメント

`scripts/`内に入っているスクリプトの使用方法を解説しています。

## backup_db.py

db.sqlite3 からデータベースのバックアップを作成するスクリプト。

### 使用方法

```bash
python backup_db.py <プレフィックス>
```
この時、 `db_files/<ブランチ名>/<プレフィックス>_<タイムスタンプ:YYYYMMDD_HHMMSS>_<Gitコミットハッシュ>.sqlite3` に出力されます。

### 使用例
```bash
# ブランチ名が "main", Gitコミットハッシュが "abcdef", プレフィックスが "1" の場合
python backup_db.py 1
```
この時、`db_files/main/1_20231001_123456_commit_abcdef.sqlite3`にバックアップが作成されます。

**注意: ブランチ名やGitコミットハッシュが取得できない場合は、"no-branch" や "no-commit" が使用されます。**


## load_db.py

db.sqlite3 からデータベースをロードするスクリプト。

### 使用方法

```bash
python load_db.py <DBファイルのパス> [--force]
```

既存のDBファイルを上書きする場合は `--force` オプションを付けてください。

### 使用例

```bash
python load_db.py db_files/main/1_20231001_123456_commit_abcdef.sqlite3 --force
```

`db_files/main/1_20231001_123456_commit_abcdef.sqlite3`というファイルからDBを読み込む。既存の `db.sqlite3` がこのファイルに置き換わるイメージ。