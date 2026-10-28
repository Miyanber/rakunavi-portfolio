// 基本、スクリプトは小さく割って必要なときimportする方針
// →スクリプト評価時間が低下しパフォーマンス向上
import { setUpDarkTheme } from './theme.js';
import { initModal } from './modal.js';
import { showPopupIfNecessary } from './popup.js';
import { initBackToTop } from './backToTop.js';

document.addEventListener('DOMContentLoaded', () => {
    setUpDarkTheme();
    initBackToTop();
    initModal();

    // 残したいクエリパラメータのホワイトリスト
    // 地図・検索機能
    const ALLOWED_QUERY_KEYS = ["spot", "query", "tags"];
    const url = new URL(window.location.href);

    for (const key of Array.from(url.searchParams.keys())) {
        if (!ALLOWED_QUERY_KEYS.includes(key)) {
            url.searchParams.delete(key);
        }
    }
    // URLを清掃して表示
    window.history.replaceState(
        {},
        document.title,
        url.pathname + url.search + url.hash
    );

});

window.onload = () => {
    showPopupIfNecessary();
};
