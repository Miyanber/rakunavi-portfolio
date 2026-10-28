// 画像の入力時、
document.addEventListener("DOMContentLoaded", () => {
const maxSizeMB = 5;

// 初期プレビューの src を保存
const previewInitialSrcMap = {};
document.querySelectorAll('input[type="file"][accept^="image"]').forEach(input => {
  const previewId = input.dataset.target;
  if (previewId) {
    const preview = document.getElementById(previewId);
    if (preview) {
      // img の src を保存しておく
      previewInitialSrcMap[previewId] = preview.src;
    }
  }
});

function resetFileInput(input) {
  input.value = ""; // 一旦クリア
  if (input.value) {
    input.type = "text";
    input.type = "file";
  }

  // プレビューを元の画像に戻す
  const previewId = input.dataset.target;
  if (previewId) {
    const preview = document.getElementById(previewId);
    if (preview) {
      const initialSrc = previewInitialSrcMap[previewId] || "";
      preview.src = initialSrc;  // ✅ 元のプレビュー画像に戻す
    }
  }
}

function validateFileSize(input) {
  if (!input.files.length) return true;
  const file = input.files[0];
  const fileSizeMB = file.size / (1024 * 1024);

  if (fileSizeMB > maxSizeMB) {
    alert(`ファイルサイズは ${maxSizeMB}MB 以下にして下さい。\n選択したファイル: ${fileSizeMB.toFixed(2)}MB`);
    resetFileInput(input);
    return false;
  }
  return true;
}

document.querySelectorAll('input[type="file"][accept^="image"]').forEach(input => {
  input.addEventListener("change", function () {
    if (validateFileSize(this)) {
      // ✅ サイズOKならプレビュー表示
      const previewId = this.dataset.target;
      if (previewId) {
        const reader = new FileReader();
        reader.onload = e => {
          const preview = document.getElementById(previewId);
          if (preview) preview.src = e.target.result;
        };
        reader.readAsDataURL(this.files[0]);
      }
    }
  });
});
});
