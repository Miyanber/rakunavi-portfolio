//=============フォーム送信成功時のポップアップ================
export function showPopupIfNecessary() {
    const popup = document.querySelector('.popup');
    if (popup) {
        popup.classList.add('show');
        setTimeout(() => popup.classList.add('hide'), 2000);
    }
}
