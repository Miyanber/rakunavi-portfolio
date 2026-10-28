// csrf.jsからgetCookieをインポートしてブラウザで使えるように
import { getCookie } from './csrf.js';
window.getCookie = getCookie;

// PDFダウンロード処理
async function downloadPDF(params, filename = 'download.pdf') {
    console.log("downloadPDF called");
    console.log('CSRF token:', getCookie('csrftoken'));

    try {
        const response = await fetch('', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/octet-stream',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: params,
            credentials: 'same-origin',
        });

        if (!response.ok) {
            const responseText = await response.text();
            console.error('Download failed:', response.status, responseText);

            if (responseText === "ObjectNotFound") {
                alertError("対象のオブジェクトが見つかりませんでした。");
            } else if (responseText.includes("Weasyprint")) {
                alertError("ダウンロードに失敗しました。Weasyprint関連のエラーです。");
            } else {
                alertError();
            }

            throw new Error(`HTTP ${response.status} - ${responseText}`);
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);

        return true;
    } catch (error) {
        console.error(error);
        alertError();
        return false;
    }
}

// エラーアラート
function alertError(message = null) {
    if (message) {
        alert(message);
    } else {
        alert('ダウンロードに失敗しました。お手数ですが、開発者にお問い合わせください。');
    }
}

// ボタン制御
function disableAllSubmitButtons() {
    document.querySelectorAll('button[type="submit"]').forEach(btn => btn.disabled = true);
}
function enableAllSubmitButtons() {
    document.querySelectorAll('button[type="submit"]').forEach(btn => btn.disabled = false);
}

// 初期化確認フォームの処理
function handleInitializationConfirm(confirmInitElem, confirmInitInput, confirmInitButton, confirmInitErrorElem, confirmInitCloseButton, params, initValue) {
    return new Promise(resolve => {
        confirmInitElem.hidden = false;

        const safeResolve = val => {
            confirmInitElem.hidden = true;
            resolve(val);
        };

        const handleConfirmClick = () => {
            if (confirmInitInput.value === 'INITIALIZE') {
                params.append('init', initValue);
                safeResolve(true);
            } else {
                confirmInitErrorElem.hidden = false;
            }
        };

        confirmInitButton.onclick = handleConfirmClick;
        confirmInitCloseButton.onclick = () => safeResolve(false);
    });
}

// PDFダウンロードフォームをバインド
function bindPdfDownloadForm(formId, filenames) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', async event => {
        event.preventDefault();
        const button = event.submitter;
        const action = form.getAttribute('data-action');
        const model = button.getAttribute('data-model');

        if (!model) {
            console.error('Model not specified in button data-model attribute.');
            alertError();
            return;
        }

        const date = new Date(form.querySelector('input[name="date"]').value);
        const deadline = new Date(form.querySelector('input[name="deadline"]').value);

        disableAllSubmitButtons();
        button.classList.add('is_loading');

        const params = new URLSearchParams();
        params.append('action', action);
        params.append('model', model);
        params.append('date', date.toISOString());
        params.append('deadline', deadline.toISOString());

        if (action === 'handout_pdf_download') {
            const initInput = form.querySelector('input[name="init"]');
            const initValue = initInput ? initInput.checked : false;

            if (initValue) {
                const confirmInitElem = document.getElementById('confirm_initialization');
                const confirmInitInput = document.getElementById('confirm_initialization_input');
                const confirmInitButton = document.getElementById('confirm_initialization_button');
                const confirmInitErrorElem = document.getElementById('confirm_initialization_error_message');
                const confirmInitCloseButton = document.getElementById('confirm_initialization_close_button');

                if (!confirmInitElem || !confirmInitInput || !confirmInitButton || !confirmInitErrorElem || !confirmInitCloseButton) {
                    console.error("Initialization confirmation elements not found.");
                    alertError();
                    enableAllSubmitButtons();
                    button.classList.remove('is_loading');
                    return;
                }

                const confirmed = await handleInitializationConfirm(
                    confirmInitElem, confirmInitInput, confirmInitButton, confirmInitErrorElem, confirmInitCloseButton, params, initValue
                );
                if (!confirmed) {
                    enableAllSubmitButtons();
                    button.classList.remove('is_loading');
                    return;
                }
            }
        }

        const success = await downloadPDF(params, filenames[model]);
        if (!success) console.error(`action: ${action}, model: ${model} failed.`);

        button.classList.remove('is_loading');
        enableAllSubmitButtons();
    });
}

// ページロード時にフォームをバインド
function initPdfDownloadBindings() {
    bindPdfDownloadForm('HandoutPDFDownloadForm', {
        exhibition: '展示_説明会資料PDF(A4)_.pdf',
        food_booth: '模擬店_説明会資料PDF(B5)_.pdf',
        live_stage_performance: '野外ライブ_説明会資料PDF(B5)_.pdf',
        music_room_performance: '音楽室ライブ_説明会資料PDF(B5)_.pdf'
    });

    bindPdfDownloadForm('ReviewPDFDownloadForm', {
        exhibition: '展示_差し戻し報告PDF(B5)_.pdf',
        food_booth: '模擬店_差し戻し報告PDF(B5)_.pdf',
        live_stage_performance: '野外ライブ_差し戻し報告PDF(B5)_.pdf',
        music_room_performance: '音楽室ライブ_差し戻し報告PDF(B5)_.pdf'
    });
}

if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', initPdfDownloadBindings);
} else {
    initPdfDownloadBindings();
}
