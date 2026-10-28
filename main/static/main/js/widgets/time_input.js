function zeroPadding(number, length) {
    return String(number).padStart(length, '0');
}

function isTimeFormat(str) {
    // 時間のフォーマットを確認する正規表現 (時:分:秒)
    const regex = /^(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d$/;

    // 文字列がフォーマットに一致するか判定
    return regex.test(str);
}

function timeInput(element) {
    /**
     * 
     * @param {HTMLDivElement} div 
     */
    function setEventListener(div) {
        const input = div.querySelector('input[type=hidden]');
        const hour = div.querySelector('.time-input_hour');
        const minute = div.querySelector('.time-input_minute');

        if (isTimeFormat(input.value)) {
            const string = input.value;
            hour.value = Number(string.slice(0, 2));
            minute.value = Number(string.slice(3, 5));
        } else {
            input.value = '';
        }

        hour.addEventListener('change', e => {
            if (minute.value && hour.value) {
                input.value = `${zeroPadding(hour.value, 2)}:${zeroPadding(minute.value, 2)}:00`;
            } else {
                input.value = '';
            }
        })
        minute.addEventListener('change', e => {
            if (hour.value && minute.value) {
                input.value = `${zeroPadding(hour.value, 2)}:${zeroPadding(minute.value, 2)}:00`;
            } else {
                input.value = '';
            }
        })
    }

    const time_inputs = element.querySelectorAll("div.time_input");
    time_inputs.forEach(div => setEventListener(div));
}

document.addEventListener('DOMContentLoaded', e => timeInput(document));