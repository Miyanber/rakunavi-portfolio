from django.apps import AppConfig


class ConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'config'
    verbose_name = '管理設定'

    def ready(self):
        from config.tasks import start
        start()
        import config.signals
