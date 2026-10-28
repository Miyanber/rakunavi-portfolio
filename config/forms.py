from django import forms

class GitOperationsForm(forms.Form):
    OP_CHOICES = [
            ('none', '------'),
            ('pull', 'Git Pull'),
            ('checkout', 'Git Checkout'),
            ('status', 'Git Status'),
            ('log', 'Git Log'),
            ('collect_static', 'Collect Static Files'),
            ('restart_process', 'Run "./scripts/apply_changes.sh" which restarts daemon.'),
            ('django_log', 'Check the Django Log File'),
        ]
    operation = forms.ChoiceField(choices=OP_CHOICES, label="操作を選択",initial='none')
    arg1 = forms.CharField(
        label='引数1',
        max_length=40,
        required=False,
        widget=forms.TextInput(),
    )
