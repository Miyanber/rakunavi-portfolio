from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/dm/(?P<partner_id>\d+)/$", consumers.DMConsumer.as_asgi()),
    re_path(r"^ws/group/(?P<group_id>\d+)/$", consumers.GroupChatConsumer.as_asgi()),
    re_path(r"ws/healthcheck/$", consumers.HealthCheckConsumer.as_asgi()),
]
