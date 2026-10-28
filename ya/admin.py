from django.contrib import admin

from ya.models import *
# Register your models here.

@admin.register(ChatGroups)
class ChatGroupsAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', )
    search_fields = ('name', )

@admin.register(ChatMessages)
class ChatMessagesAdmin(admin.ModelAdmin):
    list_display = ('send_at', 'sender', 'receiver', "content", )
    search_fields = ('send_at', 'sender__username', 'receiver__username', "content", )
    list_per_page = 50

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('author', 'created_at', 'content')
    search_fields = ('author__username', 'created_at', 'content')

@admin.register(YaUserRole)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "icon")

@admin.register(YaSettings)
class YaSettingsAdmin(admin.ModelAdmin):
    list_display = ("beta",)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("sender", "post")

