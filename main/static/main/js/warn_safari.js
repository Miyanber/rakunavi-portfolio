document.addEventListener("DOMContentLoaded", () => {
    const testVideo = document.createElement('video');
    const canPlayAV1 = testVideo.canPlayType('video/mp4; codecs="av01.0.05M.08"');
    // console.log(testVideo);
    // console.log(canPlayAV1);
    if (!canPlayAV1 || canPlayAV1 === '') {
        document.getElementById('av1_fallback_message').style.display = 'block';
    }
});