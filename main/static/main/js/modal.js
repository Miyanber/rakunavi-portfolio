//=================QRコードのモーダル==============================

function buildQRCodeUrl(baseUrl) {
    const thisUrl = window.location.href.split('?')[0];   //クエリパラメータ除去
    return `${baseUrl}?url=${encodeURIComponent(thisUrl)}&_=${Date.now()}`;
}

export function initModal() {
    const openBtn = document.getElementById('open-modal');
    const closeBtn = document.getElementById('close');
    const overlay = document.getElementById('modal-overlay');
    const modal = document.getElementById('modal');
    const img = document.getElementById('qrcode-img');

    let qrLoaded = false;

    if (openBtn) {
        openBtn.addEventListener('click', function () {
            openModal();
        });
    }
    document.addEventListener('keydown', event => {
        if (event.altKey && event.code === 'KeyX') {
            const isVisible = modal.style.display === 'flex';
            if (isVisible) {
                closeModal();
            } else {
                openModal();
            }
        }
    });

    // クリック・ESCでモーダルを閉じる
    closeBtn?.addEventListener('click', closeModal);
    overlay?.addEventListener('click', closeModal);

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeModal();
        }
    });

    function openModal() {
        // ★ ボタンを押した瞬間に初めてリクエスト
        if (!qrLoaded) {
            const dataUrl = openBtn?.getAttribute('data-url');
            if (dataUrl) {
                img.src = buildQRCodeUrl(dataUrl);
                qrLoaded = true;
            }
        }

        overlay.style.display = 'block';
        modal.style.display = 'flex';
        modal.classList.add('open_modal');
        modal.classList.remove('close_modal');

        setTimeout(() => modal.classList.remove('open_modal'), 350);
        //ここの時間をCSSと同期
    }

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
