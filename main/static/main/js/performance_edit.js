document.addEventListener("DOMContentLoaded", () => {
    addOrRemoveForm('song', 'songs');
    addOrRemoveForm('member', 'members');

    createSortable(document.getElementById('songs'));
    createSortable(document.getElementById('members'));

})

function fixDate(spot, dates) {
    // 野外ライブステージ
    if (spot.value == 2) {
        for (const date of dates) {
            date.selectedIndex = 1;
            date.dispatchEvent(new Event('change'));
            date.disabled = true;
        }
    } else {
        for (const date of dates) {
            date.disabled = false;
        }
    }
}