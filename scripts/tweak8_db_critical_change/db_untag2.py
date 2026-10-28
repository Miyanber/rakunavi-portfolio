# made with claude. これをpython3 manage.py shell で実行。
from django.db import connection
cursor = connection.cursor()
cursor.execute("PRAGMA foreign_keys = OFF")

tables = [
    (
        "account_emailaddress",
        """CREATE TABLE "account_emailaddress" (
            "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
            "verified" bool NOT NULL,
            "primary" bool NOT NULL,
            "user_id" bigint NOT NULL REFERENCES "config_user" ("id") DEFERRABLE INITIALLY DEFERRED,
            "email" varchar(254) NOT NULL
        )"""
    ),
    (
        "socialaccount_socialaccount",
        """CREATE TABLE "socialaccount_socialaccount" (
            "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
            "provider" varchar(200) NOT NULL,
            "uid" varchar(191) NOT NULL,
            "last_login" datetime NOT NULL,
            "date_joined" datetime NOT NULL,
            "user_id" bigint NOT NULL REFERENCES "config_user" ("id") DEFERRABLE INITIALLY DEFERRED,
            "extra_data" text NOT NULL CHECK ((JSON_VALID("extra_data") OR "extra_data" IS NULL))
        )"""
    ),
    (
        "config_ec2operationslog",
        """CREATE TABLE "config_ec2operationslog" (
            "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
            "datetime" datetime NOT NULL,
            "command" varchar(200) NOT NULL,
            "response" text NOT NULL,
            "exit_code" integer NOT NULL,
            "user_id" bigint NOT NULL REFERENCES "config_user" ("id") DEFERRABLE INITIALLY DEFERRED,
            "log_level" varchar NOT NULL
        )"""
    ),
]

for table_name, new_ddl in tables:
    backup = f"{table_name}_old"
    print(f"Processing {table_name} ...")
    cursor.execute(f'ALTER TABLE "{table_name}" RENAME TO "{backup}"')
    cursor.execute(new_ddl)
    cursor.execute(f'INSERT INTO "{table_name}" SELECT * FROM "{backup}"')
    cursor.execute(f'DROP TABLE "{backup}"')
    print(f"  Done.")

cursor.execute("PRAGMA foreign_keys = ON")
print("\n全テーブル修正完了")

# 確認
for table_name, _ in tables:
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE name='{table_name}'")
    sql = cursor.fetchone()[0]
    ok = "config_user" in sql and "main_user" not in sql
    print(f"{'✓' if ok else '✗'} {table_name}")
