export function setUpSideMenu() {
        const menu = document.getElementById('side-menu');
        const overlay = document.getElementById('overlay');
        const menuBtn = document.getElementById('menu-btn');
        const closeBtn = document.getElementById('close-btn');

        let startX = 0;
        let currentX = 0;
        let isDragging = false;
        const menuWidth = 280;

        // メニュー開閉の基本関数
        const openMenu = () => {
            menu.classList.add('open');
            overlay.classList.add('active');
            menu.style.transform = ''; // インラインスタイルをリセット
        };

        const closeMenu = () => {
            menu.classList.remove('open');
            overlay.classList.remove('active');
            menu.style.transform = ''; // インラインスタイルをリセット
        };

        // ボタンイベント
        menuBtn.addEventListener('click', openMenu);
        closeBtn.addEventListener('click', closeMenu);
        overlay.addEventListener('click', closeMenu);

        // タッチイベントの実装
        window.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            // 左端(30px以内)からの開始、または既にメニューが開いている場合のみドラッグを許可
            if (startX < 30 || menu.classList.contains('open')) {
                isDragging = true;
                menu.style.transition = 'none'; // ドラッグ中はアニメーションを無効化
            }
        });

        window.addEventListener('touchmove', (e) => {
            if (!isDragging) return;

            currentX = e.touches[0].clientX;
            let diff = currentX - startX;

            if (menu.classList.contains('open')) {
                // メニューが開いている時：左方向へのスワイプを検知
                let move = Math.min(0, diff);
                if (move < -menuWidth) move = -menuWidth;
                menu.style.transform = `translateX(${move}px)`;
            } else {
                // メニューが閉じている時：右方向へのスワイプを検知
                let move = Math.min(menuWidth, diff);
                if (move < 0) move = 0;
                menu.style.transform = `translateX(calc(-100% + ${move}px))`;
            }
        });

        window.addEventListener('touchend', (e) => {
            if (!isDragging) return;
            isDragging = false;
            menu.style.transition = 'transform 0.3s ease-out';

            let diff = currentX - startX;

            if (menu.classList.contains('open')) {
                // 一定以上左にスワイプしたら閉じる
                if (diff < -100) {
                    closeMenu();
                } else {
                    openMenu();
                }
            } else {
                // 一定以上右にスワイプしたら開く
                if (diff > 100) {
                    openMenu();
                } else {
                    closeMenu();
                }
            }
        });
    }