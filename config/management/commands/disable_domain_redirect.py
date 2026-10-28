from django.core import cache as django_cache
from django.core.management.base import BaseCommand

from config.models import NewDomainRedirectURL


class Command(BaseCommand):
    help = "新ドメインへのリダイレクトを無効化します"

    def handle(self, *args, **options):
        try:
            obj = NewDomainRedirectURL.objects.get(pk=1)
        except NewDomainRedirectURL.DoesNotExist:
            self.stdout.write(self.style.ERROR("NewDomainRedirectURL が存在しません"))
            return

        if not obj.active:
            self.stdout.write(self.style.WARNING("リダイレクトは既に無効化されています"))
            return

        obj.active = False
        obj.save()

        django_cache.cache.delete("new_domain_redirect")

        self.stdout.write(self.style.SUCCESS(f"✅ リダイレクトを無効化しました（URL: {obj.url}）"))
