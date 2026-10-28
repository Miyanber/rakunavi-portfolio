from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from config.models import NewDomainRedirectURL


@receiver(post_save, sender=NewDomainRedirectURL)
def clear_redirect_cache(sender, **kwargs):
    cache.delete("new_domain_redirect")
