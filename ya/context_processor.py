from ya.utils.notification import get_notification
from ya.models import YaSettings, ChatMessages
from django.db.models import Q

def main(request):
    # CONTEXTがユーザー認証前提なので、ユーザー認証で分岐の必要がある
    context  = {}
    if not "ya/" in request.path or not request.user.is_authenticated:  # YaでないURL、ログインしていない場合は返さない
        return context
    if request.user.is_ya_user:
        pass    # --> ЯのURLかつ、is_ya_userの場合返す。なくてもいいけど読みやすいように。
    else:
        return context
    
    # 本来django.contrib.messagesを使いたいが、オブジェクト名が競合するのでsessionで実装
    context["notification"] = get_notification(request)
    context["ya_settings"] = YaSettings.objects.first()
    
    context["dm_unreads"] = ChatMessages.objects.filter(
        Q(receiver=request.user)
    ).exclude(read_by=request.user).distinct()

    context["group_unreads"] = ChatMessages.objects.filter(
        Q(receiver_group__members=request.user)).exclude(read_by=request.user).distinct().values_list("receiver_group_id", flat=True)
    

    return context
