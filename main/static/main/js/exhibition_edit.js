import { getCookie } from './csrf.js';

async function postData(urlParams) {
    return await fetch('', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: urlParams,
    });
}

document.addEventListener("DOMContentLoaded", () => {
    // 並び替え
    Sortable.create(document.getElementById("events"), {
        animation: 150,
        handle: ".event_form__drag_indicator",
        onSort: () => updateOrdering(),
    });

    // 初期バインド
    bindEventButtons();
});

function bindEventButtons(root = document) {
    // 新規イベント追加
    root.querySelectorAll(".event_create_form__button button").forEach(btn => {
        btn.addEventListener("click", () => addEvent(btn));
    });

    // イベント削除
    root.querySelectorAll(".event_form__delete_button").forEach(btn => {
        btn.addEventListener("click", () => deleteEvent(btn));
    });

    // タイムスロット追加（新旧どちらのクラス名も対応）
    root.querySelectorAll(
        ".timeslot_form__add_button, .event_form__content__timeslots__append__form__button"
    ).forEach(btn => {
        btn.addEventListener("click", () => addTimeSlot(btn));
    });

    // タイムスロット削除
    root.querySelectorAll(
        ".event_form__content__timeslots__timeslot__delete_button"
    ).forEach(btn => {
        btn.addEventListener("click", () => deleteTimeSlot(btn));
    });

    root.querySelectorAll(
        ".event_form__content__timeslots__append__button"
    ).forEach(btn => {
        btn.addEventListener("click", () => showTimeSlotForm(btn));
    });
}

function updateOrdering() {
    const eventForms = document.getElementsByClassName('event_form');
    const indexElements = document.getElementsByClassName('event_form__header__index');
    for (let i = 0; i < eventForms.length; i++) {
        indexElements[i].textContent = i + 1;
        const eventIndex = parseInt(eventForms[i].getAttribute('data-index'), 10);
        const orderElement = document.getElementById(`id_event-${eventIndex - 1}-order`);
        orderElement.value = i + 1;
    }
}

function showTimeSlotForm(button) {
    const timeslotForm = document.getElementById(button.getAttribute('data-timeslot-form-id'));
    timeslotForm.classList.remove('hidden');
}

async function addTimeSlot(button) {
    const eventPk = button.getAttribute('data-pk');
    const dateSelectElem = document.getElementsByName(eventPk + '-timeslot-date')[0];
    const startAtElem = document.getElementsByName(eventPk + '-timeslot-begin_at')[0];
    const endAtElem = document.getElementsByName(eventPk + '-timeslot-end_at')[0];
    let dateElem = null;
    for (const elem of dateSelectElem.children) {
        if (elem.selected) {
            dateElem = elem;
            break;
        }
    }
    if (!dateSelectElem.reportValidity() || !startAtElem.reportValidity() || !endAtElem.reportValidity()) {
        return;
    }
    const formData = new URLSearchParams();
    formData.append('form_action', 'add_timeslot');
    formData.append('event_pk', eventPk);
    formData.append('date', dateElem.value);
    formData.append('begin_at', startAtElem.value);
    formData.append('end_at', endAtElem.value);

    const response = await postData(formData);
    const responseJson = await response.json();
    if (responseJson.success) {
        const timeslotTable = document.getElementById(eventPk + "-timeslot_table");
        timeslotTable.innerHTML = responseJson.timeslots_template;
        dateElem.selected = false;
        startAtElem.value = '';
        endAtElem.value = '';

        // 新しく描画された部分にも再度バインド
        bindEventButtons(timeslotTable);
    } else {
        console.warn(responseJson.message);
    }
}

async function deleteTimeSlot(button) {
    const timeslotPk = button.getAttribute('data-pk');
    const formData = new URLSearchParams();
    formData.append('form_action', 'delete_timeslot');
    formData.append('timeslot_pk', timeslotPk);

    const response = await postData(formData);
    const responseJson = await response.json();
    if (responseJson.success) {
        const timeslotTableRow = document.getElementById("timeslot-" + timeslotPk);
        timeslotTableRow.remove();
    } else {
        console.warn(responseJson.message);
    }
}

async function addEvent(button) {
    const nameElem = document.getElementsByName('event-new-name')[0];
    const spotSelectElem = document.getElementsByName('event-new-spot')[0];
    const explanationElem = document.getElementsByName('event-new-explanation')[0];
    let spotElem = null;
    for (const elem of spotSelectElem.children) {
        if (elem.selected) {
            spotElem = elem;
            break;
        }
    }
    if (!nameElem.reportValidity() || !spotSelectElem.reportValidity() || !explanationElem.reportValidity()) {
        return;
    }
    const formData = new URLSearchParams();
    formData.append('form_action', 'add_event');
    formData.append('name', nameElem.value);
    formData.append('spot', spotElem.value);
    formData.append('explanation', explanationElem.value);
    formData.append('order', document.getElementsByClassName('event_form').length + 1);

    const response = await postData(formData);
    const responseJson = await response.json();
    if (responseJson.success) {
        const eventFormsetElement = document.getElementById("events");
        eventFormsetElement.insertAdjacentHTML("beforeend", responseJson.event_template);

        nameElem.value = '';
        spotElem.selected = false;
        explanationElem.value = '';

        // 追加されたイベントフォームにも再度バインド
        const newForm = eventFormsetElement.lastElementChild;
        bindEventButtons(newForm);
    } else {
        console.warn(responseJson.message);
    }
}

async function deleteEvent(button) {
    if (!window.confirm('本当にこのイベントを削除しますか？※この操作は元に戻せません。')) {
        return;
    }
    const eventPk = button.getAttribute('data-pk');
    const formData = new URLSearchParams();
    formData.append('form_action', 'delete_event');
    formData.append('event_pk', eventPk);

    const response = await postData(formData);
    const responseJson = await response.json();
    if (responseJson.success) {
        const eventForm = document.getElementById(`event-${eventPk}-form`);
        eventForm.remove();
        updateOrdering();
    } else {
        console.warn(responseJson.message);
    }
}
