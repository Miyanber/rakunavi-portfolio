import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.shortcuts import get_object_or_404
from django.utils import formats
from django.utils.timezone import localtime
from django.contrib.auth import get_user_model

from ya.models import ChatMessages, ChatGroups

User = get_user_model()


def room_name_for(u1, u2):
    a, b = sorted([int(u1), int(u2)])
    return f"dm_{a}_{b}"


class DMConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.partner_id = int(self.scope["url_route"]["kwargs"].get("partner_id"))

        if not self.user.is_authenticated or not self.partner_id:
            await self.close()
            return

        self.room_name = room_name_for(self.user.id, self.partner_id)
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # 接続時はまず自分に届いている未読（相手→自分）を既読にする（返却IDsをroom全体へ通知）
        read_ids = await self.mark_messages_read_and_get_ids()
        if read_ids:
            # broadcast read event to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.read_all",  # group event -> handler chat_read_all
                    "reader_id": self.user.id,
                    "message_ids": read_ids,
                }
            )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        """
        Expect client messages with:
         - {"type": "send", "content": "..."}
         - {"type": "read"}  -> mark unread (partner->me) as read, notify group (chat.read)
         - {"type": "read_all"} -> Discord-style: mark all messages between the two as read, notify group (chat.read_all)
         - {"type": "typing", "is_typing": true/false}
        """
        msg_type = content.get("type")

        if msg_type == "send":
            text = content.get("content", "").strip()
            if not text:
                return
            # create message and broadcast
            message = await self.create_message_and_payload(text)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.message",
                    "message": message,
                }
            )

        elif msg_type == "read":
            message_ids = await self.mark_messages_read_and_get_ids()
            if message_ids:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat.read",
                        "reader_id": self.user.id,
                        "message_ids": message_ids,
                    }
                )

        elif msg_type == "read_all":
            message_ids = await self.mark_all_messages_read_and_get_ids()
            if message_ids:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat.read_all",
                        "reader_id": self.user.id,
                        "message_ids": message_ids,
                    }
                )

        elif msg_type == "typing":
            is_typing = bool(content.get("is_typing", False))
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.typing",
                    "user_id": self.user.id,
                    "is_typing": is_typing,
                }
            )

    # ----- group handlers (called by Channels) -----
    async def chat_message(self, event):
        # event["message"] is a dict produced by create_message_and_payload
        await self.send_json({
            "type": "message",
            "message": event["message"],
        })

    async def chat_read(self, event):
        await self.send_json({
            "type": "read",
            "message_ids": event["message_ids"],
            "reader_id": event["reader_id"],
        })

    async def chat_read_all(self, event):
        await self.send_json({
            "type": "read_all",
            "message_ids": event["message_ids"],
            "reader_id": event["reader_id"],
        })

    async def chat_typing(self, event):
        await self.send_json({
            "type": "typing",
            "user_id": event["user_id"],
            "is_typing": event["is_typing"],
        })

    # ----- DB helpers -----
    @database_sync_to_async
    def create_message_and_payload(self, text):
        """
        Create ChatMessages row, add sender to read_by, and return a serializable dict.
        This runs in a thread (sync) and may access ORM freely.
        """
        partner = get_object_or_404(User, id=self.partner_id)
        msg = ChatMessages.objects.create(
            sender=self.user,
            receiver=partner,
            content=text,
        )
        # sender is immediately in read_by
        msg.read_by.add(self.user)

        # build payload
        sender_icon = None
        try:
            if getattr(msg.sender, "icon", None):
                sender_icon = msg.sender.icon.url
        except Exception:
            sender_icon = None

        send_at = formats.date_format(localtime(msg.send_at))
        payload = {
            "id": msg.id,
            "content": msg.content,
            "sender_id": msg.sender.id,
            "sender_icon": sender_icon,
            "send_at": send_at,
            "read_by_count": msg.read_by.count(),
        }
        return payload

    @database_sync_to_async
    def mark_messages_read_and_get_ids(self):
        """
        Mark unread messages that partner sent to self as read.
        Return list of message ids changed.
        """
        try:
            partner = User.objects.get(id=self.partner_id)
        except User.DoesNotExist:
            return []

        qs = ChatMessages.objects.filter(
            sender=partner,
            receiver=self.user,
        ).exclude(read_by=self.user)

        ids = []
        for m in qs:
            m.read_by.add(self.user)
            ids.append(m.id)

        return ids

    @database_sync_to_async
    def mark_all_messages_read_and_get_ids(self):
        """
        Discord-style: mark all messages between the two users as read (both directions).
        Return list of message ids changed.
        """
        qs = ChatMessages.objects.filter(
            receiver_group__isnull=True,
        ).filter(
            sender_id__in=[self.user.id, self.partner_id],
            receiver_id__in=[self.user.id, self.partner_id],
        ).exclude(read_by=self.user)

        ids = []
        for m in qs:
            m.read_by.add(self.user)
            ids.append(m.id)

        return ids


# グループ
class GroupChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        try:
            self.group_id = int(self.scope["url_route"]["kwargs"]["group_id"])
        except Exception:
            await self.close()
            return

        if not self.user.is_authenticated:
            await self.close()
            return

        self.group = await database_sync_to_async(get_object_or_404)(ChatGroups, id=self.group_id)
        is_member = await self.is_member()
        if not is_member:
            await self.close()
            return

        self.room_group_name = f"group_{self.group_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # 接続時：未読（自分が未読のメッセージ）を既読化して room に通知
        read_ids = await self.mark_unread_and_get_ids()
        if read_ids:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.read_all",  # -> handler chat_read_all
                    "reader_id": self.user.id,
                    "message_ids": read_ids,
                }
            )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        """
        Client -> Server messages:
         - {"type":"send", "content":"..."}
         - {"type":"read"}  : mark unread->read for this user (partner->me semantics)
         - {"type":"read_all"} : mark all group messages as read by this user (Discord-style)
         - {"type":"typing", "is_typing": true/false}
        """
        msg_type = content.get("type")
        if msg_type == "send":
            text = content.get("content", "").strip()
            if not text:
                return
            payload = await self.create_group_message_payload(text)
            # broadcast new message to group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.message",
                    "message": payload,
                }
            )

        elif msg_type == "read":
            # mark unread messages in this group as read for this user
            ids = await self.mark_unread_and_get_ids()
            if ids:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat.read",
                        "reader_id": self.user.id,
                        "message_ids": ids,
                    }
                )

        elif msg_type == "read_all":
            ids = await self.mark_all_group_messages_read_and_get_ids()
            if ids:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "chat.read_all",
                        "reader_id": self.user.id,
                        "message_ids": ids,
                    }
                )

        elif msg_type == "typing":
            is_typing = bool(content.get("is_typing", False))
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat.typing",
                    "user_id": self.user.id,
                    "is_typing": is_typing,
                }
            )

    # ---------------- group handlers (Channels will call these)
    async def chat_message(self, event):
        await self.send_json({
            "type": "message",
            "message": event["message"],
        })

    async def chat_read(self, event):
        await self.send_json({
            "type": "read",
            "message_ids": event["message_ids"],
            "reader_id": event["reader_id"],
        })

    async def chat_read_all(self, event):
        await self.send_json({
            "type": "read_all",
            "message_ids": event["message_ids"],
            "reader_id": event["reader_id"],
        })

    async def chat_typing(self, event):
        await self.send_json({
            "type": "typing",
            "user_id": event["user_id"],
            "is_typing": event["is_typing"],
        })

    # ---------------- DB helpers (sync code executed in thread)
    @database_sync_to_async
    def is_member(self):
        return self.group.members.filter(id=self.user.id).exists()

    @database_sync_to_async
    def create_group_message_payload(self, text):
        # create record
        msg = ChatMessages.objects.create(
            sender=self.user,
            receiver_group=self.group,
            content=text,
        )
        msg.read_by.add(self.user)
        # prepare JSON-serializable payload
        sender_icon = None
        try:
            if getattr(self.user, "icon", None):
                sender_icon = self.user.icon.url
        except Exception:
            sender_icon = None
        payload = {
            "id": msg.id,
            "content": msg.content,
            "sender_id": self.user.id,
            "sender_username": self.user.username,
            "sender_icon": sender_icon,
            "send_at": formats.date_format(localtime(msg.send_at)),  # string
            "read_by_count": msg.read_by.count(),
            "member_count": self.group.members.count(),
        }
        return payload

    @database_sync_to_async
    def mark_unread_and_get_ids(self):
        # mark messages in this group that this user hasn't read
        qs = ChatMessages.objects.filter(
            receiver_group=self.group
        ).exclude(read_by=self.user)
        ids = []
        for m in qs:
            m.read_by.add(self.user)
            ids.append(m.id)
        return ids

    @database_sync_to_async
    def mark_all_group_messages_read_and_get_ids(self):
        # For "read_all" semantics: same as mark_unread_and_get_ids for group
        return self.mark_unread_and_get_ids()


class HealthCheckConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.close()
