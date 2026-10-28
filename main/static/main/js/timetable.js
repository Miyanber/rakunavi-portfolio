document.addEventListener("DOMContentLoaded", () => {
    const button_on = document.getElementById("full-screen");
    button_on.onclick = () => {
        window.scroll(0, 0);
        const timetable = document.querySelector(".timetable-spots");
        timetable.classList.add("full-screen");
        const background = document.querySelector(".background");
        background.classList.add("full-screen");
        window.scroll(0, 0);
    }
    const button_off = document.getElementById("cancel");
    button_off.onclick = () => {
        const timetable = document.querySelector(".timetable-spots");
        timetable.classList.remove("full-screen");
        const background = document.querySelector(".background");
        background.classList.remove("full-screen");
    }
})

function showEventDetail(eventId) {
    const detail = document.getElementById(`event_detail_${eventId}`);
    detail.hidden = false;
    const overlayDark = document.getElementById("overlay_dark");
    overlayDark.hidden = false;
}

function closeEventDetail(eventId) {
    const detail = document.getElementById(`event_detail_${eventId}`);
    detail.hidden = true;
    const overlayDark = document.getElementById("overlay_dark");
    overlayDark.hidden = true;
}