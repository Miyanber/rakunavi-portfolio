# １度きりの通知を作成・削除

def set_notification(request, level, text):
    request.session["notification"] = {
        "level": level,
        "text": text,
    }

def get_notification(request):
    return request.session.pop("notification", None)
