(() => {
    const CACHE_KEY = "ws_available_cache";
    const CACHE_TTL = 5 * 60 * 1000; // 5分
    const TIMEOUT_MS = 1500;

    function getCachedResult() {
        try {
            const raw = localStorage.getItem(CACHE_KEY);
            if (!raw) return null;
            const { value, ts } = JSON.parse(raw);
            if (Date.now() - ts > CACHE_TTL) return null;
            return value;
        } catch {
            return null;
        }
    }

    function setCachedResult(value) {
        try {
            localStorage.setItem(
                CACHE_KEY,
                JSON.stringify({ value, ts: Date.now() })
            );
        } catch { }
    }

    function testWebSocket(timeoutMs) {
        return new Promise((resolve) => {
            let finished = false;
            let ws;

            const finish = (result) => {
                if (finished) return;
                finished = true;
                try { ws && ws.close(); } catch { }
                resolve(result);
            };

            try {
                ws = new WebSocket(WS_TEST_URL);
            } catch {
                finish(false);
                return;
            }

            const timer = setTimeout(() => finish(false), timeoutMs);

            ws.onopen = () => {
                clearTimeout(timer);
                finish(true);
            };

            ws.onerror = () => {
                clearTimeout(timer);
                finish(false);
            };

            ws.onclose = () => {
                clearTimeout(timer);
                finish(false);
            };
        });
    }

    async function init() {
        // 非表示タブでは実行しない
        if (document.visibilityState !== "visible") return;

        const indicator = document.getElementById("websocket-indicator");
        if (!indicator) return;

        const cached = getCachedResult();
        if (cached !== null) {
            window.USE_WS = cached;
            indicator.textContent = cached
                ? "WebSocket available"
                : "WebSocket unavailable";
            indicator.classList.toggle("unavailable", !cached);
            return;
        }

        const available = await testWebSocket(TIMEOUT_MS);
        setCachedResult(available);

        window.USE_WS = available;
        indicator.textContent = available
            ? "WebSocket available"
            : "WebSocket unavailable";
        indicator.classList.toggle("unavailable", !available);
    }

    // DOM 準備後に 1 回だけ
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init, { once: true });
    } else {
        init();
    }
})();
