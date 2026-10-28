from colorama import init, Back, Fore, Style
init(autoreset=True) 
import difflib, subprocess


# プロジェクトの依存関係確認
def check_dependencies():
    _result = subprocess.run(
        ".venv/bin/pip3 freeze",
        shell=True,
        capture_output=True,
        text=True,
    )
    installed_packages = [line.strip() for line in _result.stdout.splitlines()]
    try:
        with open('requirements.txt', 'r') as txt:
            required_packages = [line.strip() for line in txt.readlines()]
    except Exception as e:
        print(f"FATAL: {e}")
        required_packages = []
    
    diff = difflib.context_diff(
        installed_packages, 
        required_packages, 
        fromfile="現在の環境", 
        tofile="requirements"
    )
    sm = difflib.SequenceMatcher(None, installed_packages, required_packages)
    # 判定
    if not int(sm.ratio()) == int(1):   #型厳しくそろえる
        print(Back.WHITE + Fore.RED + "[check_dependencies] 警告：仮想環境とrequirements.txtの依存関係が一致しません。")
        for line in diff:
            print(line)
        print(Back.WHITE + Fore.RED + "[check_dependencies] requirements.txtもしくは仮想環境をアップデートする必要があるでしょう。")

# 外部から利用できるよう関数化はしてある
check_dependencies()
