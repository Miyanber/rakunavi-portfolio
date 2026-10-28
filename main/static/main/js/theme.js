// ========== ダークモード設定 ==========
export function applyTheme(mode, animate = true) {
    const apply = () => {
        document.body.classList.toggle('dark-mode', mode === 'dark');
        document.body.classList.toggle('light-mode', mode === 'light');
        localStorage.setItem('theme', mode);
    };

    if (animate && document.startViewTransition) {
        document.body.classList.add('theme-changing');

        const transition = document.startViewTransition(apply);

        // トランジション完了後にクラスを削除
        transition.finished.finally(() => {
            document.body.classList.remove('theme-changing');
        });
    } else {
        apply();
    }
}

export function setUpDarkTheme() {
    const toggleButton = document.getElementById('dark-mode-toggle');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedMode = localStorage.getItem('theme');
    const initialMode = savedMode || (prefersDark ? 'dark' : 'light');

    applyTheme(initialMode, false);

    toggleButton?.addEventListener('click', () => {
        const newMode = document.body.classList.contains('dark-mode') ? 'light' : 'dark';
        applyTheme(newMode);
    });

    document.addEventListener('keydown', event => {
        if (event.altKey && event.code === 'KeyC') {
            const newMode = document.body.classList.contains('dark-mode') ? 'light' : 'dark';
            applyTheme(newMode);
        }
    });

    // 確実に描画後に解除
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            document.body.classList.add('ready');
            document.body.classList.remove('no-animation');
        });
    });
}
