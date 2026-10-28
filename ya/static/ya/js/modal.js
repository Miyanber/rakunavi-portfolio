//=================QRコードのモーダル==============================

function buildQRCodeUrl(baseUrl) {
    const thisUrl = window.location.href.split('?')[0];   //クエリパラメータ除去
    return `${baseUrl}?url=${encodeURIComponent(thisUrl)}&_=${Date.now()}`;
}

export function initModal() {
    const openBtn = document.querySelectorAll('.open-modal');
    const closeBtn = document.getElementById('close');
    const overlay = document.getElementById('modal-overlay');
    const modal = document.getElementById('modal');
    const img = document.getElementById('qrcode-img');

    let qrLoaded = false;

    
        openBtn.forEach(btn => {
            btn.addEventListener('click', function () {

            // ★ ボタンを押した瞬間に初めてリクエスト
            if (!qrLoaded) {
                const baseUrl = btn.getAttribute('data-url');
                 img.src = buildQRCodeUrl(baseUrl);
                if (baseUrl) {
                    img.src = buildQRCodeUrl(baseUrl);
                    qrLoaded = true;
                }
            }

            overlay.style.display = 'block';
            modal.style.display = 'flex';
            modal.classList.add('open_modal');
            modal.classList.remove('close_modal');

            setTimeout(() => modal.classList.remove('open_modal'), 350);
            //ここの時間をCSSと同期
        });
    });

    // クリック・ESCでモーダルを閉じる
    closeBtn?.addEventListener('click', closeModal);
    overlay?.addEventListener('click', closeModal);

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeModal();
        }
    });

    function closeModal() {
        overlay.style.display = 'none';
        modal.classList.remove('open_modal');
        modal.classList.add('close_modal');

        setTimeout(() => {
            // アニメーション後にクラス削除しておく
            modal.classList.remove('close_modal');
            modal.style.display = 'none';
        }, 400);
        //ここの時間をCSSと同期
    }
}
