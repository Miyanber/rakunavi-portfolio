// 開始スプリクト

// キャンバスの位置をarticleに一致させる
const canvas = document.getElementById('scene');
canvas_top = window.sessionStorage.getItem("article_top");
canvas_left = window.sessionStorage.getItem("article_left");
canvas.style.top = canvas_top + "px";
canvas.style.left = canvas_left + "px";


// flowers呼び出し
width = window.sessionStorage.getItem("article_width");
height = window.sessionStorage.getItem("article_height");
window.startFlowerEffect({
    width: width,
    height: height,
    baseCount: 25,
    upDraft: 0.01,
    windAmp: 1.5,
    petalMin: 8,
    petalMax: 14
});
