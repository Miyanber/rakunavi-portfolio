from django.contrib.admin import AdminSite
from django.urls import path, reverse_lazy
from functools import update_wrapper
from django.template.response import TemplateResponse
from django.shortcuts import redirect


class RakuNaviAdminSite(AdminSite):
    def get_urls(self):

        def wrap(view, cacheable=False):
            def wrapper(*args, **kwargs):
                return self.admin_view(view, cacheable)(*args, **kwargs)

            wrapper.admin_site = self
            # Used by LoginRequiredMiddleware.
            wrapper.login_url = reverse_lazy("admin:login", current_app=self.name)
            return update_wrapper(wrapper, view)
        
        urls = super().get_urls()
        custom_urls = [
            path('rakunavi_actions/', wrap(self.rakunavi_actions), name="rakunavi_actions"),
        ]
        return custom_urls + urls
    
    def rakunavi_actions(self, request, extra_context=None):
        """
        らくなび用アクションをこのページにまとめる
        """
        app_list = self.get_app_list(request)

        context = {
            **self.each_context(request),
            "title": 'らくなびアクション',
            "subtitle": None,
            "app_list": app_list,
            **(extra_context or {}),
        }

        request.current_app = self.name
        
        # 展示の作成はコマンドで行うようになりました。
        # TODO: adminのHTMLから削除が必要
        # if request.method == "POST":
        #     if request.POST.get('action_type') == 'create_exhibitions':
        #         create_exhibitions(request)
        #     return redirect('admin:rakunavi_actions')
            
        context['status'] = request.GET.get('message')
        
        return TemplateResponse(
            request, self.index_template or "admin/rakunavi_actions.html", context
        )


rakunavi_admin_site = RakuNaviAdminSite(name='rakunavi_admin')

from django.contrib import admin
from django.contrib.sites.models import Site
from django.contrib.auth.models import Permission

for model, modeladmin in admin.site._registry.items():
    rakunavi_admin_site.register(model, modeladmin.__class__)
    