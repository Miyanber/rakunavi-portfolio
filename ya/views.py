from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.views.generic.edit import FormMixin
from django.db.models import Q, Count, Prefetch
from django.db import IntegrityError
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView, FormView, CreateView, UpdateView, DeleteView
from django.views.decorators.http import require_POST
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.utils import formats
from django.shortcuts import render


from urllib.parse import urlparse, urlunparse, unquote

from ya.models import *
from ya.forms import *
from ya.utils.notification import set_notification

from datetime import timedelta
import mojimoji

# Create your views here.
class YaMixedIn(UserPassesTestMixin):
    def test_func(self) -> bool:
        if self.request.user.is_authenticated:  # is_developerを使う際はまずこれで分岐しないといけない
            if self.request.user.is_ya_user or self.request.user.is_superuser:  
                return True
        else:
            return False

    def handle_no_permission(self):
        raise Http404()


class DirectMessagesListView(YaMixedIn, ListView):
    template_name = "ya/dm_listview.html"
    model = ChatMessages
    context_object_name = "dm_list"

    def get_queryset(self):
        user = self.request.user

        # ① DMのみ（グループ除外）かつ自分が関与しているメッセージ
        messages = (
            ChatMessages.objects
            .filter(
                receiver_group__isnull=True
            )
            .filter(
                Q(sender=user) | Q(receiver=user)
            )
            .select_related("sender", "receiver")
            .prefetch_related("receiver__role")
            .order_by("-send_at")
        )

        # ② 相手ユーザーごとに最新1件を抽出
        latest_messages = {}
        for msg in messages:
            if msg.sender == user:
                partner = msg.receiver
            else:
                partner = msg.sender

            if partner and partner.id not in latest_messages:
                latest_messages[partner.id] = msg

        # ③ send_at の降順で並び替え
        return sorted(
            latest_messages.values(),
            key=lambda x: x.send_at,
            reverse=True
        )


class DirectMessageView(YaMixedIn, FormMixin, ListView):
    template_name = "ya/dm.html"
    model = ChatMessages
    form_class = DirectMessageForm
    context_object_name = "messages"

    def get_partner(self):
        return get_object_or_404(User.objects.select_related("role"), id=self.kwargs["user_id"])

    def get_queryset(self):
        user = self.request.user
        partner = self.get_partner()

        return (
            ChatMessages.objects
            .filter(receiver_group__isnull=True)
            .filter(
                Q(sender=user, receiver=partner) |
                Q(sender=partner, receiver=user)
            )
            .select_related("sender", "receiver")
            .order_by("send_at")
            .annotate(read_count=Count("read_by"))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["partner"] = self.get_partner()
        context["form"] = self.get_form()
        context["three_days_ago"] = timezone.now() - timedelta(days=3)
        return context

    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        form = self.get_form()

        if form.is_valid():
            msg = ChatMessages.objects.create(
                sender=request.user,
                receiver=self.get_partner(),
                content=form.cleaned_data["content"],
            )
            msg.read_by.add(request.user)

            # Ajax の場合
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({
                    "id": msg.id,
                    "content": msg.content,
                    "send_at": formats.date_format(msg.send_at, "DATETIME_FORMAT"),
                    "sender_icon": msg.sender.icon.url if msg.sender.icon else "",
                })

            return super().form_valid(form)

        return self.form_invalid(form)

    def form_valid(self, form):
        return super().get(self.request)

    def get_success_url(self):
        return reverse("ya:dm", kwargs={"user_id": self.get_partner().id})

    def dispatch(self, request, *args, **kwargs):
        """
        表示時に未読メッセージを既読化
        """
        response = super().dispatch(request, *args, **kwargs)

        user = request.user
        partner = self.get_partner()

        unread_messages = ChatMessages.objects.filter(
            sender=partner,
            receiver=user,
            receiver_group__isnull=True
        ).exclude(read_by=user)

        for msg in unread_messages:
            msg.read_by.add(user)

        return response


class DirectMessagePollView(YaMixedIn, View):
    def get(self, request, *args, **kwargs):
        user = request.user
        partner = get_object_or_404(User, id=kwargs["user_id"])
        last_id = request.GET.get("last_id", 0)

        messages = (
            ChatMessages.objects
            .filter(
                receiver_group__isnull=True,
                id__gt=last_id,
            )
            .filter(
                Q(sender=user, receiver=partner) |
                Q(sender=partner, receiver=user)
            )
            .select_related("sender")
            .order_by("send_at")
        )

        data = []
        for msg in messages:
            data.append({
                "id": msg.id,
                "content": msg.content,
                "sender_id": msg.sender.id,
                "sender_icon": (
                    msg.sender.icon.url
                    if msg.sender.icon
                    else ""
                ),
                "send_at": msg.send_at.strftime("%H:%M"),
                "is_mine": msg.sender == user,
            })

        return JsonResponse({"messages": data})


class DirectMessageReadView(YaMixedIn, View):
    def post(self, request, *args, **kwargs):
        user = request.user
        partner = get_object_or_404(User, id=kwargs["user_id"])

        unread = ChatMessages.objects.filter(
            sender=partner,
            receiver=user,
            receiver_group__isnull=True
        ).exclude(read_by=user)

        for msg in unread:
            msg.read_by.add(user)

        return JsonResponse({"status": "ok"})
    

class GroupListView(YaMixedIn, ListView):
    template_name = "ya/group_listview.html"
    model = ChatGroups
    context_object_name = "groups"

    def get_queryset(self):
        # 有効（is_visible）で、ユーザーが含まれるもの
        return (super().get_queryset()
            .filter(members__in=[self.request.user])
            .filter(is_visible=True)
            .prefetch_related("messages", "members")
            )


class GroupChatView(YaMixedIn, TemplateView):
    template_name = "ya/group_chat.html"

    def test_func(self):
        super().test_func()
        group_id = self.kwargs.get("group_id")
        obj = get_object_or_404(ChatGroups, id=group_id)
        if self.request.user.is_superuser:
            return True
        elif self.request.user in obj.members.all() and  obj.is_visible:  # メンバー以外見れない
            return True
        else:
            return False
        
    def handle_no_permission(self):
        return redirect('ya:group_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group_id = self.kwargs.get("group_id")
        # 事前にメンバー数を数えたりで大幅に最適化する
        group = get_object_or_404(
            ChatGroups.objects
                .annotate(members_count=Count("members"))
                .prefetch_related("members__role"),
                id=group_id
            )
        # messages (last 300)
        messages = ChatMessages.objects\
            .filter(receiver_group=group)\
            .order_by("-send_at")[:300]\
            .select_related("sender")\
            .prefetch_related("read_by")\
            .annotate(read_count=Count("read_by"))
        context.update({
            "group": group,
            "messages": reversed(messages),
            "form": DirectMessageForm(),
        })
        return context


class PostsListView(YaMixedIn, ListView, FormMixin):
    template_name = "ya/posts_listview.html"
    model = Post
    paginate_by = 15
    form_class = PostForm

    def get_queryset(self):
        return (
            Post.objects
            .filter(is_visible=True, reply_to__isnull=True)
            .select_related("author", "author__role")
            .prefetch_related("liked", "replies")
            .order_by("-created_at")
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["a_week_ago"] = timezone.now() - timedelta(days=7)
        context["submit_token"] = uuid.uuid4().hex
        
        queryset = self.get_queryset()
        paginator = Paginator(queryset, self.paginate_by) 
        page_number = self.request.GET.get("page", 1)
        try:
            page_obj = paginator.page(page_number)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        context["posts"] = page_obj #pageオブジェクトにしないとページネーションが動作しない
        return context
    
    def post(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        form = self.get_form()

        if form.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)
    
    def form_valid(self, form):
        token = self.request.POST.get("submit_token")
        if not token:
            return self.form_invalid(form)
        # 同じ token が存在するかチェック
        if Post.objects.filter(submit_token=token).exists():
            # 二重送信の場合はリダイレクト
            return redirect(self.get_success_url())

        post = form.save(commit=False)
        post.author = self.request.user
        post.is_visible = True
        post.submit_token = token
        post.save()

        set_notification(self.request, "success", "投稿を作成しました。")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("ya:posts_listview")

# いいねの切り替え 
@login_required
@require_POST
def toggle_like(request):
    post_id = request.POST.get("post_id")
    post = get_object_or_404(Post, id=post_id)

    if request.user in post.liked.all():
        post.liked.remove(request.user)
        liked = False
    else:
        post.liked.add(request.user)
        liked = True

        # --- 通知の作成（いいねされた時のみ） ---
        if post.author != request.user:
            # 重複通知を防ぐ（すでに同じ投稿にいいね通知があれば作成しない等）
            Notification.objects.get_or_create(
                sender=request.user,
                recipient=post.author,
                post=post,
                action_type='like'
            )

    return JsonResponse({
        "liked": liked,
        "like_count": post.liked.count(),
    })


@login_required
def post_delete(request, post_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    post = get_object_or_404(Post, id=post_id)

    # 権限チェック
    if post.author == request.user or request.user.is_superuser:
        # 論理削除
        post.is_visible = False
        post.save(update_fields=["is_visible"])
        return JsonResponse({"success": True})

    return JsonResponse({"error": "Permission denied"}, status=403)


class PostDetailView(YaMixedIn, CreateView):
    model = Post
    template_name = "ya/post_detail.html"
    model_form = PostForm
    fields = ("content", "image", )

    def get_object(self, queryset=None):
        replies_qs = (
            Post.objects
            .filter(is_visible=True)
            .select_related("author")
            .order_by("-created_at")
        )

        return get_object_or_404(
            Post.objects
            .filter(is_visible=True)
            .prefetch_related(
                Prefetch(
                    "replies",
                    queryset=replies_qs,
                    to_attr="visible_replies",
                )
            ),
            id=self.kwargs["post_id"],
        )

    def get_queryset(self):
        # is_visible=Trueだけ
        return super().get_queryset().filter(is_visible=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        user = self.request.user
        
        context["replies"] = post.visible_replies   #最適化
        context["is_liked"] = post.liked.filter(id=user.id).exists()
        context["like_count"] = post.liked.count()
        context["post"] = post
        context["a_week_ago"] = timezone.now() - timedelta(days=7)
        
        return context
    
    def form_valid(self, form):
        post = form.save(commit=False)
        post.author = self.request.user
        post.is_visible = True
        post.reply_to = self.get_object()

        post.save()
        set_notification(self.request, "success", "投稿に返信しました。")
        # 自分の投稿への返信以外の場合に通知を送る
        obj = self.get_object()
        if obj.author != self.request.user:
            Notification.objects.create(
                sender=self.request.user,
                recipient=obj.author,
                post=obj, # 親投稿をセット
                action_type='reply'
            )
        return super().form_valid(form)

    def get_success_url(self):
        obj = self.get_object()
        return reverse_lazy("ya:post_detail", kwargs={'post_id' : obj.id})


class SearchUserView(YaMixedIn, ListView):
    template_name = "ya/search_user.html"
    form_class = SearchUserForm
    model = User
    context_object_name = "users"

    def get_form(self):
        return SearchUserForm(self.request.GET or None)
    
    def get_queryset(self):
        queryset =  super().get_queryset().exclude(id=self.request.user.pk).order_by('?')[:5]    #デフォルトではおすすめとしてランダムに5件取得
        self.request.session["form_is_valid"] = False   #テンプレで使う
        form = self.get_form()
        if form.is_valid(): #検索があった場合のみ
            self.request.session["form_is_valid"] = True
            query = form.cleaned_data.get('query')  #入力
            query_filter = Q()
            if query:
                # 入力されたクエリを全角から半角に変換＋半角でも全角に変換
                normalized_query = mojimoji.zen_to_han(query)
                wide_query = mojimoji.han_to_zen(query)
                normalized_keywords = normalized_query.split()  # スペースで区切る
                wide_keywords = wide_query.split()
                for keyword in (normalized_keywords + wide_keywords):
                    query_filter |= Q(
                        Q(username__icontains=keyword) |
                        Q(user_id__icontains=keyword)
                        # 検索範囲, 大文字小文字区別せず含むかどうか
                    )
                    queryset = User.objects.all().exclude(id=self.request.user.pk).filter(query_filter).order_by("-date_joined")

        return queryset

    def get_context_data(self, **kwargs):
        context =  super().get_context_data(**kwargs)
        context["form"] = SearchUserForm(self.request.GET)
        return context


class UserProfileView(YaMixedIn, TemplateView):
    template_name = "ya/user_profile_posts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.kwargs.get('user_id')
        profile_user = get_object_or_404(User.objects.select_related("role"), user_id=user_id)
        context['profile_user'] = profile_user
        return context


class UserInfoChangeView(YaMixedIn, UpdateView):
    model = User
    template_name = "ya/userinfo_change.html"
    form_class = UserInfoForm

    def get_object(self, queryset=None):
        # URLの <str:user_id> を使って編集対象のユーザーを取得
        return get_object_or_404(User, user_id=self.kwargs.get('user_id'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ベーステンプレートが期待している変数名 'profile_user' をセット
        # self.get_object() は上で定義した get_object を呼び出します
        context['profile_user'] = self.get_object() 
        return context

    def test_func(self):
        # 自分のアカウントのみ編集可能
        return self.request.user == self.get_object()

    def get_success_url(self):
        # 保存完了後、そのユーザーのプロフィール画面（user_profile）にリダイレクトする
        # self.object は更新された後のユーザーデータです
        set_notification(self.request, "success", "保存しました。")
        return reverse_lazy("ya:user_profile", kwargs={'user_id': self.object.user_id})


class UserPasswordChangeView(YaMixedIn, PasswordChangeView):
    template_name = "ya/password_change.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile_user'] = self.request.user #テンプレート動作のため必要
        return context

    def get_success_url(self):
        set_notification(self.request, "success", "パスワードを変更しました。")
        return reverse_lazy("ya:user_profile", kwargs={'user_id': self.request.user.user_id})


class GroupSettingsView(YaMixedIn, UpdateView):
    model = ChatGroups
    template_name = "ya/group_settings.html"
    form_class = GroupSettingsForm

    def test_func(self):
        if self.request.user in self.get_object().members.all():
            return True
        else:
            return False
    
    def form_valid(self, form):
        if form.cleaned_data.get("is_visible"):
            set_notification(self.request, "success", "保存しました。")
        else:
            set_notification(self.request, "success", "グループを削除しました。")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["group"] = self.get_object()
        return context
    
    def get_success_url(self):
        return reverse_lazy("ya:group_chat", kwargs={'group_id':self.get_object().pk})


@login_required
def group_member_add(request, group_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    user_id = request.POST.get("user_id")
    if not user_id:
        return JsonResponse({"error": "ユーザーIDが未入力です"}, status=400)

    group = get_object_or_404(ChatGroups, id=group_id)
    user = get_object_or_404(User, user_id=user_id)

    if request.user not in group.members.all():
        return JsonResponse({"error": "Permission denied"}, status=403)
    elif group.members.filter(id=user.id).exists():
        return JsonResponse({"error": "すでに追加されています"}, status=400)

    group.members.add(user)
    return JsonResponse({"success": True})


@login_required
def group_member_remove(request, group_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    user_id = request.POST.get("user_id")

    group = get_object_or_404(ChatGroups, id=group_id)
    user = get_object_or_404(User, user_id=user_id)

    if request.user not in group.members.all():
        return JsonResponse({"error": "Permission denied"}, status=403)
    elif not group.members.filter(id=user.id).exists():
        return JsonResponse({"error": "メンバーではありません"}, status=400)
    elif group.members.count() <= 1:
        return JsonResponse({"error": "最後の1人は削除できません"}, status=400)
    elif user == request.user:
            return JsonResponse({"error": "自分自身は削除できません"}, status=400)

    group.members.remove(user)
    return JsonResponse({"success": True})


class GroupQuickCreateView(YaMixedIn, View):
    def post(self, request, *args, **kwargs):
        group = ChatGroups.objects.create(
            name="新しいグループ",
        )
        group.members.add(request.user)

        return redirect(
            reverse("ya:group_settings", kwargs={"pk": group.id})
        )


class NotificationListView(YaMixedIn, ListView):
    model = Notification
    template_name = "ya/notification_list.html"
    context_object_name = "notifications"

    def get_queryset(self):
        # 自分宛の通知のみ取得
        queryset = Notification.objects.filter(recipient=self.request.user).select_related('sender', 'post')
        
        # このページを表示した瞬間に、未読通知をすべて既読にする
        queryset.filter(is_read=False).update(is_read=True)
        
        return queryset


class AboutView(YaMixedIn, TemplateView):
    template_name = "ya/about.html"
