document.addEventListener("DOMContentLoaded", function () {
    const map = document.getElementById("map");

    if (map.complete) {
        // 画像がすでに読み込まれている場合、すぐにレイアウト計算を行う
        calculateLayout();
    } else {
        // 画像が読み込まれていない場合は、loadイベントを待つ
        map.addEventListener('load', calculateLayout);
    }

    function calculateLayout() {
        const spots = document.querySelectorAll(".spot");
        const locationIcon = document.getElementById('location_icon');
        // #mapの幅、高さ
        const mapWidth = map.offsetWidth;
        const mapHeight = map.offsetHeight;

        spots.forEach(function (spot) {
            const startX = spot.getAttribute("data-start-x");
            const startY = spot.getAttribute("data-start-y");
            const item_width = spot.getAttribute("data-item-width");
            const item_height = spot.getAttribute("data-item-height");

            const left = (startX / 100) * mapWidth;
            const top = (startY / 100) * mapHeight;
            const set_width = (item_width / 100) * mapWidth;
            const set_height = (item_height / 100) * mapHeight;

            spot.style.left = `${left}px`;
            spot.style.top = `${top}px`;
            spot.style.width = `${set_width}px`;
            spot.style.height = `${set_height}px`;
        });

        // LocationIconの方
        if (locationIcon) {
            // data属性から座標を取得
            const startX = parseFloat(locationIcon.getAttribute('data-start-x')) || 0;
            const startY = parseFloat(locationIcon.getAttribute('data-start-y')) || 0;
            const item_width = parseFloat(locationIcon.getAttribute("data-item-width"));
            const item_height = parseFloat(locationIcon.getAttribute("data-item-height"));

            // マップの横幅に基づいて位置を計算
            const leftPosition = (startX / 100) * mapWidth;
            const topPosition = (startY / 100) * mapHeight;
            const set_width = (item_width / 100) * mapWidth;
            const set_height = (item_height / 100) * mapHeight;

            // 計算した位置をスタイルに適用
            locationIcon.style.left = `${leftPosition}px`;
            locationIcon.style.top = `${topPosition}px`;
            locationIcon.style.width = `${set_width}px`;
            locationIcon.style.height = `${set_height}px`;
        }
    }
});

new ScrollHint('.js-scrollable', {
    i18n: {
        scrollable: 'スクロールできます'
    }
});