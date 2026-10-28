from django.apps import AppConfig
from django.db.models.signals import post_migrate


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'
    verbose_name = '文化祭'
    
    def ready(self):
        from . import signals
        post_migrate.connect(signals.create_default_groups, sender=self)
        post_migrate.connect(signals.create_default_allergens, sender=self)
