from pathlib import Path
import os, dj_database_url, sys
from dotenv import load_dotenv
from django.utils.csp import CSP

# overrideをTrueにしないとシステム環境変数が優先される？
load_dotenv('.env', override=True)
load_dotenv('.env.development', override=True)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG') == 'True'

# 独自の変数で、デプロイのSSL化が終わればTrue、作業中はFalseにする。HTTPS強制処理などを分岐する。
DEPLOY_DONE = os.environ.get('DEPLOY_DONE', False)

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '127.0.0.1').split(",")

# Django 4.0から必須化、mypageのダウンロードではCSRFトークン検証に必要？
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS','http://127.0.0.1').split(",")

# Application definition

INSTALLED_APPS = [
    "daphne",
    "django_http_compression",
    'baton', # contrib.adminより上
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    "channels",
    "django_apscheduler",
    'main',
    'config',
    'sports_fes',
    'ya',
        
    # "debug_toolbar",  #後で追加する
    # 'django_cleanup.apps.CleanupConfig', # 画像の削除を行うためのアプリ。今後は容量に余裕があるため、削除しない。
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'storages',
    'django_ckeditor_5',     #リッチテキストのサポートの最新版(4は情報が多いがサ終)
    'pwa',
    'django.contrib.sitemaps',
    'baton.autodiscover', #1番最後
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "django_http_compression.middleware.HttpCompressionMiddleware", #Gzipに代わる圧縮Middleware
    # 'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # "debug_toolbar.middleware.DebugToolbarMiddleware",  #ここに入れるので10番目
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    'allauth.account.middleware.AccountMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # 'rakunavi.middleware.RateLimitMiddleware',
    # 'config.middleware.ProjectLastUpdatedMiddleware',
    "config.middleware.NewDomainRedirectMiddleware",    #ドメイン移行用
]

AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',
]

ACCOUNT_FORMS = {
    'login': 'main.forms.CustomLoginForm',
}

SOCIALACCOUNT_FORMS = {
    'signup': 'main.forms.CustomSignupForm',
}

INTERNAL_IPS = [
    "127.0.0.1",
]

# デバッグツールバー
if DEBUG and "test" not in sys.argv:
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE.insert(10, "debug_toolbar.middleware.DebugToolbarMiddleware")
# 管理サイトで無効化する
if DEBUG:
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": lambda request: not request.path.startswith("/admin/")
    }

ROOT_URLCONF = 'rakunavi.urls'

# CSRFエラーページのカスタム
CSRF_FAILURE_VIEW = 'main.views.custom_csrf_fail'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'), 
            os.path.join(BASE_DIR, 'templates', 'allauth')
        ],
        'APP_DIRS': False,
        'OPTIONS': {
            'loaders': [    #キャッシュローダー有効
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                
                'django.template.context_processors.request',
                "django.template.context_processors.csp", #CSPのnonce追加用
                'main.context_to_base.common', # 全ビューで利用可能なデータを記述
                'main.context_to_base.main',    #文化祭用
                'main.context_to_base.user_groups', # ユーザーのグループ情報を記述
                'sports_fes.context_processors.common_context', 
                'ya.context_processor.main',
            ],
        },
    },
]


from django.utils.log import DEFAULT_LOGGING 

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[{server_time}] {message}",
            "style": "{",
        },
        "file": {
            "format": "[%(asctime)s] %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            # "filters": ["require_debug_true"],
            "class": "logging.StreamHandler",
        },
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/rakunavi/django.log', # 本番環境のログファイルパス
            "formatter": "file",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "mail_admins", "file"],
            "level": "INFO",
        },
        "django.request": {
            "handlers": ["console", "file"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["django.server", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


if DEBUG:
    LOGGING['handlers']['file']['filename'] = "django.log"  # 開発環境のログファイルパス

# DaphneはASGIなので不要
# WSGI_APPLICATION = 'rakunavi.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'ja'

TIME_ZONE = 'Asia/Tokyo'

USE_I18N = True

USE_L10N = True

USE_TZ = True

FORMAT_MODULE_PATH = 'rakunavi.formats'


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

CLOUD_SERVICE = os.environ.get('CLOUD_SERVICE')
ENVIRONMENT = os.environ.get('ENVIRONMENT')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'CONN_MAX_AGE' : 60,
    }
}

CDN_DOMAIN = "127.0.0.1:8000"
if ENVIRONMENT == 'production':
    CDN_DOMAIN = os.environ.get('CDN_DOMAIN')

    STORAGES = {
        "staticfiles": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": {
                "access_key": os.environ.get('AWS_ACCESS_KEY_ID'),
                "secret_key": os.environ.get('AWS_SECRET_ACCESS_KEY'),
                "bucket_name": os.environ.get('AWS_STORAGE_BUCKET_NAME'),
                "region_name": os.environ.get('AWS_S3_REGION_NAME'),
                "custom_domain": f"{CDN_DOMAIN}",
                "location": "static/",
            },
        },
        "default": {
            "BACKEND": "rakunavi.storages.MediaStorage",
            "OPTIONS": {
                "access_key": os.environ.get('AWS_ACCESS_KEY_ID'),
                "secret_key": os.environ.get('AWS_SECRET_ACCESS_KEY'),
                "bucket_name": os.environ.get('AWS_STORAGE_BUCKET_NAME'),
                "region_name": os.environ.get('AWS_S3_REGION_NAME'),
                "custom_domain": f"{CDN_DOMAIN}",
                "location": "media/",
            },
        },
    }

    # # AWS S3 の設定
    # AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    # AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    #CKEditorでファイルアップロードに必要
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    # AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME')
    # AWS_S3_CUSTOM_DOMAIN = f"{CDN_DOMAIN}"

    # # 静的ファイル（CSS / JS など）
    # STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
    # STATIC_URL = f"https://{CDN_DOMAIN}/static/"
    # STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

    # # メディアファイル（画像アップロードなど）
    # DEFAULT_FILE_STORAGE = "rakunavi.storages.MediaStorage"
    # MEDIA_URL = f"https://{CDN_DOMAIN}/media/"
    # MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

elif ENVIRONMENT == 'local':
    STATIC_URL = '/static/'
    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
    STATICFILES_DIRS = [
        os.path.join(BASE_DIR, "static")
    ]
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

else:
    raise ValueError("ENVIRONMENT in .env must be either 'production' or 'local'.")


# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'config.User'

LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "main:mypage"
LOGOUT_REDIRECT_URL = "main:index"

EMAIL_REQUIRED = False
# Django-allauth の仕様変更で以下のようにする
ACCOUNT_LOGIN_METHODS = ['username']
ACCOUNT_SIGNUP_FIELDS = ['username*', 'password1*', 'password2*']
# Django 5.2 以降で出る runserver 警告の抑止
DJANGO_RUNSERVER_HIDE_WARNING = True
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'


# CKEditorの設定
customColorPalette = [
    {
        'color': 'hsl(4, 90%, 58%)',
        'label': 'Red'
    },
    {
        'color': 'hsl(340, 82%, 52%)',
        'label': 'Pink'
    },
    {
        'color': 'hsl(291, 64%, 42%)',
        'label': 'Purple'
    },
    {
        'color': 'hsl(262, 52%, 47%)',
        'label': 'Deep Purple'
    },
    {
        'color': 'hsl(231, 48%, 48%)',
        'label': 'Indigo'
    },
    {
        'color': 'hsl(207, 90%, 54%)',
        'label': 'Blue'
    },
]

CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': {
            'items': [
                'heading', '|', 'bold', 'italic', 'link',
                'bulletedList', 'numberedList', 'blockQuote'
            ],
        },
        'language': 'ja',

    },
    'extends': {
        'blockToolbar': [
            'paragraph', 'heading1', 'heading2', 'heading3',
            '|',
            'bulletedList', 'numberedList',
            '|',
            'blockQuote',
        ],
        'toolbar': {
            'items': [
                'undo', 'redo', '|', 'heading', 'fontFamily',  '|',
                'bold', 'italic', 'link', 'underline', 'strikethrough', 'subscript', 'superscript', '|',
                'alignment', 'outdent', 'indent', 'horizontalLine',  '|',
                'sourceEditing', 'showBlocks', '|',
                'bulletedList', 'numberedList', 'todoList', 'blockQuote', '|',
                'specialCharacters', 'removeFormat', 'insertTable', '|',
                'fullscreen', 
            ],
            'shouldNotGroupWhenFull': 'true'
        },
        'table': {
            'contentToolbar': [ 'tableColumn', 'tableRow', 'mergeTableCells',
            'tableProperties', 'tableCellProperties' ],
            'tableProperties': {
                'borderColors': customColorPalette,
                'backgroundColors': customColorPalette,
                'defaultProperties': {
                    'borderStyle': 'solid',
                    'borderWidth': '1px',
                    'borderColor': customColorPalette,
                    'borderCollapse': 'collapse',
                }
            },
            'tableCellProperties': {
                'borderColors': customColorPalette,
                'backgroundColors': customColorPalette,
                'defaultProperties': {
                    'borderStyle': 'solid',
                    'borderWidth': '1px',
                    'borderColor': customColorPalette
                }
            }
        },
        'heading' : {
            'options': [
                { 'model': 'paragraph', 'title': 'Paragraph', 'class': 'ck-heading_paragraph' },
                { 'model': 'heading1', 'view': 'h1', 'title': 'Heading 1', 'class': 'ck-heading_heading1' },
                { 'model': 'heading2', 'view': 'h2', 'title': 'Heading 2', 'class': 'ck-heading_heading2' },
                { 'model': 'heading3', 'view': 'h3', 'title': 'Heading 3', 'class': 'ck-heading_heading3' }
            ]
        },
        'language': 'ja',
    },
    # media
    'media': {
        'blockToolbar': [
            'paragraph', 'heading1', 'heading2', 'heading3',
            '|',
            'bulletedList', 'numberedList',
            '|',
            'blockQuote',
        ],
        'toolbar': {
            'items': ['heading', '|', 'outdent', 'indent', '|', 'bold', 'italic', 'link', 'underline', 'strikethrough',
                    'code','subscript', 'superscript', 'highlight', '|', 'codeBlock', 'sourceEditing', 'insertImage',
                    'bulletedList', 'numberedList', 'todoList', '|',  'blockQuote', 'imageUpload', '|',
                    'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', 'mediaEmbed', 'removeFormat',
                    'insertTable',
                    ],
            'shouldNotGroupWhenFull': True
        },
        'image': {
            'toolbar': ['imageTextAlternative', '|', 'imageStyle:alignLeft',
                        'imageStyle:alignRight', 'imageStyle:alignCenter', 'imageStyle:side',  '|'],
            'styles': [
                'full',
                'side',
                'alignLeft',
                'alignRight',
                'alignCenter',
            ]

        },
        'table': {
            'contentToolbar': [ 'tableColumn', 'tableRow', 'mergeTableCells',
            'tableProperties', 'tableCellProperties' ],
            'tableProperties': {
                'borderColors': customColorPalette,
                'backgroundColors': customColorPalette
            },
            'tableCellProperties': {
                'borderColors': customColorPalette,
                'backgroundColors': customColorPalette
            }
        },
        'heading' : {
            'options': [
                { 'model': 'paragraph', 'title': 'Paragraph', 'class': 'ck-heading_paragraph' },
                { 'model': 'heading1', 'view': 'h1', 'title': 'Heading 1', 'class': 'ck-heading_heading1' },
                { 'model': 'heading2', 'view': 'h2', 'title': 'Heading 2', 'class': 'ck-heading_heading2' },
                { 'model': 'heading3', 'view': 'h3', 'title': 'Heading 3', 'class': 'ck-heading_heading3' }
            ]
        }
    },
    'list': {
        'properties': {
            'styles': 'true',
            'startIndex': 'true',
            'reversed': 'true',
        }
    },
    'safer': {
        'blockToolbar': [
            'paragraph', 'heading1', 'heading2', 'heading3',
            '|',
            'bulletedList', 'numberedList',
            '|',
            'blockQuote',
        ],
        'toolbar': {
            'items': [
                'undo', 'redo', '|', 'heading', 'fontFamily',  '|',
                'bold', 'italic', 'link', 'underline', 'strikethrough', 'subscript', 'superscript', '|',
                'alignment', 'outdent', 'indent', 'horizontalLine',  '|',
                'showBlocks', '|',
                'bulletedList', 'numberedList', 'todoList', 'blockQuote', '|',
                'specialCharacters', 'removeFormat', 'insertTable', '|',
                'fullscreen', 
            ],
            'shouldNotGroupWhenFull': 'true'
        },
        'table': {
            'contentToolbar': [ 'tableColumn', 'tableRow', 'mergeTableCells',
            'tableProperties', 'tableCellProperties' ],
            'tableProperties': {
                'borderColors': customColorPalette,
                'backgroundColors': customColorPalette
            },
            'tableCellProperties': {
                'borderColors': customColorPalette,
                'backgroundColors': customColorPalette
            }
        },
        'heading' : {
            'options': [
                { 'model': 'paragraph', 'title': 'Paragraph', 'class': 'ck-heading_paragraph' },
                { 'model': 'heading1', 'view': 'h1', 'title': 'Heading 1', 'class': 'ck-heading_heading1' },
                { 'model': 'heading2', 'view': 'h2', 'title': 'Heading 2', 'class': 'ck-heading_heading2' },
                { 'model': 'heading3', 'view': 'h3', 'title': 'Heading 3', 'class': 'ck-heading_heading3' }
            ]
        },
        'language': 'ja',
    },
}

CKEDITOR_5_UPLOAD_FILE_TYPES = ["jpeg", "png", "gif", "webp", "tiff", "avif"]
CKEDITOR_5_UPLOAD_PATH = "images/ck_uploads/" 
CKEDITOR_5_MAX_FILE_SIZE = 3

# CDNドメインを利用し、プロトコル付きのURLに
if CDN_DOMAIN == "127.0.0.1:8000" or DEPLOY_DONE== False:
    CDN_DOMAIN_WITH_PROTOCOL = "http://" + CDN_DOMAIN   #httpsでは動作しないため
else:
    CDN_DOMAIN_WITH_PROTOCOL = "https://" + CDN_DOMAIN

DOCS_IMAGES_URL = f"{CDN_DOMAIN_WITH_PROTOCOL}/docs-images"
# 管理サイト拡張のBATONの設定
BATON = {
    'SITE_HEADER': 'らくなび',
    'SITE_TITLE': 'らくなび',
    'INDEX_TITLE': 'Django管理ページDashboard',
    'SUPPORT_HREF': 'https://github.com/your-username/rakunavi-portfolio/issues',
    'COPYRIGHT': 'Copyright © 2024 Rakunavi Development Team', # HTML is safe
    'POWERED_BY': 'Rakunavi Development Team', # HTML is safe
    'CONFIRM_UNSAVED_CHANGES': True,
    'SHOW_MULTIPART_UPLOADING': True,
    'ENABLE_IMAGES_PREVIEW': True,
    'CHANGELIST_FILTERS_IN_MODAL': False,
    'CHANGELIST_FILTERS_ALWAYS_OPEN': False,
    'CHANGELIST_FILTERS_FORM': False,
    'CHANGEFORM_FIXED_SUBMIT_ROW': True,
    'COLLAPSABLE_USER_AREA': True,
    'MENU_ALWAYS_COLLAPSED': False,
    'MENU_TITLE': 'メインメニュー',
    'MESSAGES_TOASTS': True, # True for all, or e.g. ['warning', 'error']
    'LOGIN_SPLASH': f'{CDN_DOMAIN_WITH_PROTOCOL}/static/main/img/toji_temple.webp', # ログイン画面背景
    'GRAVATAR_ENABLED' : False,
    'FORCE_THEME': None, # 'light' or 'dark', or None to allow user toggle
    'IMAGE_PREVIEW_WIDTH': 200,
    'MENU': (
        { 'type': 'title', 'label': 'クイックアクセス', 'apps': ('main', 'auth', ), 'icon': 'apps'},    #タイトル
            { 'type': 'model', 'label': '権限管理', 'app':'config', 'name': 'permission', 'icon': 'lock',},
            { 'type': 'model', 'label': 'ユーザー', 'app':'main', 'name': 'user', 'icon': 'person',},
            { 'type': 'model', 'label': '展示', 'app':'main', 'name': 'exhibition', 'icon': 'festival',},
            { 'type': 'model', 'label': '模擬店', 'app':'main', 'name': 'foodbooth', 'icon': 'award_meal',},
            { 'type': 'model', 'label': 'ライブ', 'app':'main', 'name': 'performance', 'icon': 'music_note',},
            { 'type': 'model', 'label': '場所', 'app':'main', 'name': 'spot', 'icon': 'location_on',},
        { 'type': 'title', 'label': 'その他', 'apps': ('main', 'auth', ), 'icon': 'other_admission'},
            { 'type': 'free', 'label': '管理ページへ', 'url': '/management/', 'icon': 'link',},
    )
}

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

PWA_SERVICE_WORKER_PATH = os.path.join(BASE_DIR, 'main', 'static', 'main', 'js', 'service_worker.js')   #Service_workerのJSをオーバーライド

# サイトマップ用、sitesから選択
SITE_ID = int(os.environ.get('SITE_ID', 1))

# AVIF変換時の一時保存場所
IMAGEKIT_CACHEFILE_DIR = 'imagekit/cache'

# channel化
ASGI_APPLICATION = "rakunavi.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],  # Redis のホスト:ポート。環境変数で管理するのが望ましい？
        },
    },
}


"""
セキュリティ設定群
"""

if DEPLOY_DONE:     #SSL化完了したら適用
    # 海外からの接続ブロック用
    USE_X_FORWARDED_HOST = True
    USE_X_FORWARDED_PORT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # セッションのセキュリティ強化
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "None"
    # CSRFの設定
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = "None"

    """CSPヘッダ設定 （拒否せずエラーを出す）
            CDNなどの外部のスクリプトやCSSを利用する場合、ここにドメインを登録する。
            SECURE_CSPの場合、登録しないと、読み込みが拒否される。"""
    SECURE_CSP = {
        "default-src": [CSP.SELF],

        "script-src": [
            CSP.SELF,
            CDN_DOMAIN,
            CSP.UNSAFE_INLINE,
            "https://unpkg.com",
            "https://www.googletagmanager.com",
            "https://platform.twitter.com",
            "https://www.line-website.com",
            "https://cdn.jsdelivr.net/",
            "https://cdnjs.cloudflare.com",
            "https://cdn.plyr.io",
            "https://static.cloudflareinsights.com"
        ],

        "style-src": [
            CSP.SELF,
            CDN_DOMAIN,
            CSP.UNSAFE_INLINE,
            "https://fonts.googleapis.com",
            "https://unpkg.com",
            "https://cdn.plyr.io",
        ],

        "img-src": [
            CSP.SELF,
            CDN_DOMAIN,
            "data:",
            "https:",
        ],

        "font-src": [
            CSP.SELF,
            CDN_DOMAIN,
            "https://fonts.gstatic.com",
        ],

        "connect-src": [
            CSP.SELF,
            CDN_DOMAIN,
            "https://www.google-analytics.com",
            "https://region1.google-analytics.com",
            "https://unpkg.com",
            "https://cdn.plyr.io",
            "https://cdn.jsdelivr.net",
        ],

        "frame-src": [
            CSP.SELF,
            CDN_DOMAIN,
            "https://social-plugins.line.me",
            "https://platform.twitter.com",
            "https://www.google.com",
        ],
    }

    # SecurityMiddlewareがHSTSヘッダを設定するために記述
    SECURE_HSTS_SECONDS = 31536000      #1年
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD  = True
