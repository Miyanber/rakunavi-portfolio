// 二重送信時を防止
document.querySelector("form").addEventListener("submit", () => {
    const btn = document.getElementById("post-btn");
    btn.disabled = true;
    this.querySelector("button[type=submit]").disabled = true;
});


// 画像ダイアログ処理等
const imageInput = document.getElementById("image-input");
const uploadIcon = document.getElementById("image-upload-icon");
const wrapper = document.getElementById("post-image-wrapper");
const preview = document.getElementById("preview-image");
const clearBtn = document.getElementById("clear-image-btn");

// アイコンをクリック → ファイル選択ダイアログを開く
uploadIcon.addEventListener("click", () => {
    imageInput.click();
});

// ファイル選択 → プレビュー表示
imageInput.addEventListener("change", () => {
    const file = imageInput.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        preview.src = e.target.result;
        wrapper.style.display = "block"; // プレビュー表示
    };
    reader.readAsDataURL(file);
});

// クリアボタン → プレビューと input をリセット
clearBtn.addEventListener("click", () => {
    imageInput.value = "";      // ファイル選択をリセット
    preview.src = "#";          // プレビュー削除
    wrapper.style.display = "none"; // 非表示
});


// 投稿削除ロジック
document.querySelectorAll(".delete-btn").forEach(button => {
    button.addEventListener("click", () => {
        const postId = button.dataset.postId;
        if (!postId) {
            alert("不正な投稿です");
            return;
        }

        if (!confirm("この投稿を削除しますか？また未保存の内容は失われます。")) {
            return;
        }

        fetch(`/ya/posts/${postId}/delete/`, {
            method: "POST",
            headers: {
                "X-CSRFToken": window.csrftoken,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // 投稿DOMも削除
                button.closest(".unit").remove();
            } else {
                alert(data.error);
            }
        });
    });
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let cookie of cookies) {
            cookie = cookie.trim();
            if (cookie.startsWith(name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


// いいね機能
const csrftoken = getCookie("csrftoken");
document.querySelectorAll(".like-btn").forEach(btn => {
    btn.addEventListener("click", function () {
        const postId = this.dataset.postId;

        fetch(window.toggle_like_url, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": csrftoken,
            },
            body: new URLSearchParams({
                post_id: postId,
            }),
        })
        .then(response => response.json())
        .then(data => {
            const heart = this.querySelector(".heart");
            const count = this.querySelector(".like-count");

            count.textContent = data.like_count;
            this.setAttribute("aria-pressed", data.liked);
        })
        .catch(error => {
            console.error("いいね処理に失敗しました", error);
        });
    });
});


// 画像をクリックしたら別タブ表示
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".js-open-image").forEach(function (img) {
        img.addEventListener("click", function (event) {
            event.preventDefault();      // aタグの遷移を止める
            event.stopPropagation();     // 親要素への伝播を止める

            const url = img.dataset.imageUrl;
            if (url) {
                window.open(url, "_blank", "noopener");
            }
        });
    });
});
