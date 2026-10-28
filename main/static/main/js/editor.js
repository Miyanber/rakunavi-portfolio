/**
 * 追加・削除ボタンの初期設定
 * @param {String} name
 * @param {String} name_plutal
 */
function addOrRemoveForm(name, name_plutal) {
    const formset = document.getElementById(name_plutal);
    const newFormsetItem = document.getElementById(`${name}_form_dummy`);
    const addButton = document.getElementById(`${name}_add`);
    const removeButton = document.getElementById(`${name}_remove`);
    const totalFormsInput = document.querySelector(`input[name=${name}-TOTAL_FORMS]`);
    const deletedForms = document.getElementById('deleted_forms');

    // 追加処理
    addButton.onclick = e => {
        const currentItemsCount = formset.querySelectorAll('.formset_item').length;

        const newElement = newFormsetItem.cloneNode(true);
        newElement.id = '';
        newElement.classList.add('formset_item');
        newElement.hidden = false;
        newElement.innerHTML = newElement.innerHTML.replaceAll("__prefix__", totalFormsInput.value);
        newElement.innerHTML = newElement.innerHTML.replaceAll("__prefix1__", Number(totalFormsInput.value) + 1);

        const orderElem = newElement.querySelector('input.order');
        if (orderElem) {
            orderElem.value = currentItemsCount + 1;
        }

        formset.append(newElement);
        totalFormsInput.value = Number(totalFormsInput.value) + 1;

        // Widgetがある場合は読み込み必須
        previewableFileInput(formset);
        timeInput(formset);
    }

    // 削除処理
    removeButton.onclick = e => {
        const currentItems = formset.querySelectorAll('.formset_item');
        const currentItemsCount = currentItems.length;

        if (currentItemsCount === 0) {
            // リストが空なら何もしない
            console.log("List is empty. Ignorering")
            return;
        }

        if (window.confirm("本当に最後の項目を削除しますか？（変更を適用するまでは削除されません。）")) {
            const deletedItem = currentItems[currentItemsCount - 1];
            const formPrefix = deletedItem.querySelector('.index').getAttribute('form-prefix');

            if (Number(document.getElementById(`id_${name}-${formPrefix}-id`).value) > 0) {
                deletedItem.hidden = true;
                deletedForms.appendChild(deletedItem.cloneNode(true));
                deletedItem.remove();
                document.getElementById(`id_${name}-${formPrefix}-should_delete`).value = true;
            } else {
                deletedItem.remove();
                totalFormsInput.value = Number(totalFormsInput.value) - 1;
            }
        }
    }
}

/**
 * ドラッグアンドドロップの並び変え実装
 * orderフィールドを持つ前提で作成
 * @param {HTMLElement} wrapper
 */
function createSortable(wrapper) {
    Sortable.create(wrapper, {
        animation: 150,
        handle: ".drag_indicator .wrapper",
        onStart: () => onStartEvent(wrapper),
        onEnd: () => onEndEvent(wrapper),
        onChange: () => onChangeEvent(wrapper),
        onSort: () => onSortEvent(wrapper)
    });

    function onStartEvent(wrapper) {
        // console.log("onStart!!");
    }

    function onEndEvent(wrapper) {
        // console.log("onEnd!!");
    }

    function onChangeEvent(wrapper) {
        // console.log("onChange!!");
    }

    /**
     *
     * @param {HTMLElement} wrapper
     */
    function onSortEvent(wrapper) {
        console.log("onSort!!");
        const formsetItems = wrapper.querySelectorAll('.formset_item');
        formsetItems.forEach((formsetItem, index) => {
            const formIndex = index;// 0~
            // innerHTML変更後は子要素が編集不可になる
            formsetItem.querySelector('.index strong').textContent = String(formIndex + 1);// 1~
            formsetItem.querySelector('input.order').value = String(formIndex + 1);;// 1~
        })
    }
}

function scrollToError() {
    const errorElement = document.querySelector('.errorlist');
    if (errorElement) {
        errorElement.scrollIntoView({
            behavior: 'smooth'
        });
    }
}

document.addEventListener("DOMContentLoaded", () => {
    scrollToError();
});