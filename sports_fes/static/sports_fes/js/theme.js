// ========== ダークモード設定 ==========
export function applyTheme(mode) {
    document.body.classList.toggle('dark-mode', mode === 'dark');
    document.body.classList.toggle('light-mode', mode === 'light');
    localStorage.setItem('theme', mode);
}

export function setUpDarkTheme() {
    const toggleButton = document.getElementById('dark-mode-toggle');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const savedMode = localStorage.getItem('theme');
    const initialMode = savedMode || (prefersDark ? 'dark' : 'light');

    applyTheme(initialMode);

    toggleButton?.addEventListener('click', () => {
        const newMode = document.body.classList.contains('dark-mode') ? 'light' : 'dark';
        applyTheme(newMode);
    });

    // 確実に描画後に解除
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            document.body.classList.add('ready');
            document.body.classList.remove('no-animation');
        });
    });
}

