//=========スクロールしたら表示される”ページトップに戻る”ボタン==============
export function initBackToTop() {
    const btn = document.getElementById('backToTop');
    if (!btn) return;

    window.addEventListener('scroll', () => {
        if (window.scrollY > 700) {
            btn.hidden = false;
        } else {
            btn.hidden = true;
        }
    });

    // クリックでスムーズにトップへ戻る
    btn.addEventListener('click', () => {
        btn.classList.add('moving_backToTop');
        // window.scrollTo({ top: 0, behavior: 'smooth' });
        // lenisを使用するため、上のようにすると無視される
        lenis.scrollTo(0);
        setTimeout(() => {
            btn.classList.remove('moving_backToTop');
        }, 2000);
        // 十分時間取る
    });
}
