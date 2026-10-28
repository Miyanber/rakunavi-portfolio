const DEFAULT_ICON_PATH = "/static/main/img/default-icon.webp";
document.addEventListener('DOMContentLoaded', e => previewableFileInput(document));

function previewableFileInput(element) {
    /**
     * 
     * @param {HTMLDivElement} div 
     */
    function setEventListener(div) {
        const img = div.querySelector("img");
        const clearButton = div.querySelector("button.disable_checkbox_input");
        const clearCheckbox = div.querySelector("input[type=checkbox]");
        const fileButton = div.querySelector("button.file_input");
        const fileClearButton = div.querySelector("button.clear_file_input");
        const fileInput = div.querySelector("input[type=file]");
        // プレビューを行う場合（デフォルトはTrue）
        if (img) {
            fileInput.addEventListener('change', e => {
                img.src = window.URL.createObjectURL(e.target.files[0]);
                if (clearCheckbox)
                    clearCheckbox.checked = false;
            });
            if (!fileInput.value) {
                const initialURL = fileInput.dataset.initial;
                if (initialURL) {
                    img.src = initialURL;
                } else {
                    img.src = DEFAULT_ICON_PATH;
                }
            }
        }
        // "ファイルを選択"の代わりのボタン
        fileButton.onclick = () => {
            fileInput.click();
        }
        // "クリア"の代わりのボタン
        if (clearButton) {
            clearButton.onclick = () => {
                if (window.confirm("本当に写真を削除しますか？（変更ボタンを押すまでは削除されません。）")) {
                    clearCheckbox.checked = true;
                    img.src = DEFAULT_ICON_PATH;
                }
            }
        }
        // ファイルの選択を解除するボタン
        if (fileClearButton) {
            fileClearButton.onclick = () => {
                fileInput.value = "";
                img.src = DEFAULT_ICON_PATH;
            }
        }
    }

    const previewable_file_inputs = element.querySelectorAll("div.previewable_file_input");
    previewable_file_inputs.forEach(div => setEventListener(div));
}