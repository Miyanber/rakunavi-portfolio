//  ([緯度, 経度], ズームレベル)     ズームレベル：大きいほどズーム、小さいほどルーズ
var map = L.map('mapid').setView([34.982680, 135.746754], 17);
var tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="http://osm.org/copyright">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>',
    maxZoom: 19
});
tileLayer.addTo(map);
// 物言うマーカー
var marker = L.marker([34.982680, 135.746754]).addTo(map);
marker.bindPopup("<b>是非お越し下さい！！</b>").openPopup();
