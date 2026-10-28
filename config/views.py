from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.views.generic import TemplateView, ListView, DetailView, FormView
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy

from urllib.parse import urlparse, urlunparse, unquote
import psutil, platform, subprocess

from config.forms import GitOperationsForm
from config.models import *

class  SystemMonitorView(UserPassesTestMixin, TemplateView):
    template_name = "config/system_monitor.html"

    def test_func(self):
        return self.request.user.is_superuser
    
    def handle_no_permission(self):
        raise Http404()
    
    def get_context_data(self, **kwargs):
        context =  super().get_context_data(**kwargs)
        context["os"] = platform.system()
        context["arch"] = platform.machine()
        context["cpu_model"] = platform.processor()
        context["physical_cores"] = psutil.cpu_count(logical=False)
        context["logical_cores"] = psutil.cpu_count(logical=True)
        context["total_memory"] = f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB"
        

        return context


def system_stats(request):
    if not  request.user.is_superuser:
        raise Http404()
    data = {
        "cpu": psutil.cpu_percent(interval=None),
        "memory": psutil.virtual_memory().percent,
        "swap": psutil.swap_memory().percent,
    }
    return JsonResponse(data)


class GitOperationsView(UserPassesTestMixin, FormView):
    template_name = "config/git.html"
    form_class = GitOperationsForm
    success_url = reverse_lazy('main:ec2_operations')

    def test_func(self):
        return self.request.user.is_superuser
    
    def handle_no_permission(self):
        raise Http404()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        return context

    def form_valid(self, form):
        operation = form.cleaned_data["operation"] 
        arg1 = form.cleaned_data["arg1"]
        log_level = LogLevels.INFO
        
        # デフォルトメッセージ
        self.request.session["operation_status"] = f"{operation}の操作を実行しました。"
        self.request.session["operation"] = f"操作：{operation} {arg1}"

        # 実際の操作
        try:
            if operation == "pull":
                from scripts import backup_db
                backup_db.backup_db("auto_db")  # バックアップ
                _result = subprocess.run(
                    ["git", "pull"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5,
                )
                self.request.session["operation_status"] =_result.stdout + _result.stderr
            elif operation =="checkout":
                if arg1:
                    _result = subprocess.run(
                        ["git", "checkout", arg1],
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=5,
                    )
                    self.request.session["operation_status"] =_result.stdout + _result.stderr
                else:
                    self.request.session["operation_status"] = "エラー：引数を指定してください。"
                    log_level = LogLevels.ERROR
            elif operation == "status":
                _result = subprocess.run(
                        ["git", "status"],
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=5,
                    )
                self.request.session["operation_status"] =_result.stdout + _result.stderr
            elif operation == "log":
                _result = subprocess.run(
                        ["git", "log"],
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=5,
                    )
                self.request.session["operation_status"] =_result.stdout + _result.stderr
            elif operation == "collect_static":
                _result = subprocess.run(
                    [".venv/bin/python3", "manage.py", "collectstatic", "--noinput"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30,
                )
                self.request.session["operation_status"] =_result.stdout + _result.stderr
            elif operation == "restart_process":
                subprocess.run(
                    "bash ./scripts/apply_changes.sh",
                    shell=True,     # これ必要
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10,
                )
            elif operation == "django_log":
                try:
                    _num = int(arg1)
                except ValueError:
                    _num = 50
                _result = subprocess.run(
                    f"tail /var/log/rakunavi/django.log -n {_num}",
                    shell=True,     # これ必要
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5,
                )
                self.request.session["operation_status"] = _result.stdout +  _result.stderr
            elif operation == "none":
                self.request.session["operation"] = "▓"
                self.request.session["operation_status"] = "操作を待機中......"


        except subprocess.TimeoutExpired as e:
            self.request.session["operation_status"] = f"タイムアウトしました。\nエラー： {e}"
            log_level = LogLevels.ERROR
        
        except Exception as e:
            self.request.session["operation_status"] = f"実行に失敗しました。\nエラー： {e}"
            log_level = LogLevels.FATAL

        # ログ保存
        EC2OperationsLog.objects.create(
            user = self.request.user,
            log_level = log_level,
            command = operation + arg1,
            response = self.request.session["operation_status"],
            exit_code = 1 if "エラー" in self.request.session["operation_status"] else 0        #正常終了のときは0を返す
            )
        return super().form_valid(form)
    
    
