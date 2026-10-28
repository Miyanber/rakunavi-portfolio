//以下は警告を出すコード
let isSubmittingForm = false;

function confirmInput() {
    const submit_button = document.getElementById("submit_button");
    const checkbox_confirm = document.getElementById('checkbox_confirm');
    const confirmLabel = document.getElementById("label_confirm");

    submit_button.onclick = async e => {
        submit_button.disabled = true;

        if (checkbox_confirm.checked) {
            const result = window.confirm('続行すると変更が確定します。\nよろしいですか？');
            if (result) {
                const form = document.getElementsByTagName("form")[0];
                // バリデーションはサーバー側で実装
                try {
                    document.getElementById('submit_button').textContent = "Submitting form.....";
                    document.getElementById('submit_button').style = "pointer-events:none";
                } catch {
                    console.log("Cannot display progress");
                }
                isSubmittingForm = true;
                form.submit();
            } else {
                alert('変更の送信はキャンセルされました.');
            }

        } else {
            confirmLabel.classList.add('require_confirm');
        }

        submit_button.disabled = false;
    }

    window.addEventListener('beforeunload', event => {
        // リンクやフォームが送信されていない場合にのみ警告を表示
        if (!isSubmittingForm) {
            event.preventDefault();
            event.returnValue = '警告：変更は保存されません';
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    confirmInput();
});