# made with claude. これをpython3 manage.py shell で実行。
from django.db import connection

cursor = connection.cursor()
cursor.execute("PRAGMA foreign_keys = OFF")

# バックアップ
cursor.execute("ALTER TABLE django_admin_log RENAME TO django_admin_log_old")

# config_user を参照するテーブルとして再作成
cursor.execute("""
    CREATE TABLE "django_admin_log" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "action_time" datetime NOT NULL,
        "object_id" text NULL,
        "object_repr" varchar(200) NOT NULL,
        "action_flag" smallint unsigned NOT NULL CHECK ("action_flag" >= 0),
        "change_message" text NOT NULL,
        "content_type_id" integer NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED,
        "user_id" bigint NOT NULL REFERENCES "config_user" ("id") DEFERRABLE INITIALLY DEFERRED
    )
""")

# config_user に存在するレコードだけ移行
cursor.execute("""
    INSERT INTO django_admin_log
    SELECT old.* FROM django_admin_log_old old
    INNER JOIN config_user u ON old.user_id = u.id
""")

cursor.execute("DROP TABLE django_admin_log_old")
cursor.execute("PRAGMA foreign_keys = ON")

# 確認
cursor.execute("SELECT sql FROM sqlite_master WHERE name='django_admin_log'")
print(cursor.fetchone()[0])
