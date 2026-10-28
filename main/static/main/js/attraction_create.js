document.addEventListener("DOMContentLoaded", () => {
    const congestionLevelTab = document.getElementById("congestion_level_tab");
    const waitTimeTab = document.getElementById("wait_time_tab");
    const congestionLevelTabContent = document.querySelector(".form__tab__congestion_level");
    const waitTimeTabContent = document.querySelector(".form__tab__wait_time");

    const waitTimeInput = document.getElementById("id_wait_time");

    congestionLevelTab.addEventListener("click", () => {
        if (!congestionLevelTab.classList.contains("active")) {
            congestionLevelTab.classList.add("active");
            waitTimeTab.classList.remove("active");
            congestionLevelTabContent.classList.remove("hidden");
            waitTimeTabContent.classList.add("hidden");
        }
    });

    waitTimeTab.addEventListener("click", () => {
        if (!waitTimeTab.classList.contains("active")) {
            waitTimeTab.classList.add("active");
            congestionLevelTab.classList.remove("active");
            congestionLevelTabContent.classList.add("hidden");
            waitTimeTabContent.classList.remove("hidden");
        }
    });

    // wait_time が入力されている場合は待ち時間タブを開く
    if (waitTimeInput.value !== "") {
        waitTimeTab.classList.add("active");
        congestionLevelTabContent.classList.add("hidden");
        waitTimeTabContent.classList.remove("hidden");
    } else {
        congestionLevelTab.classList.add("active");
        congestionLevelTabContent.classList.remove("hidden");
        waitTimeTabContent.classList.add("hidden");
    }

    const submitButton = document.getElementById("submit_button");
    const confirmCheckbox = document.getElementById("checkbox_confirm");
    const confirmLabel = document.getElementById("label_confirm");

    const form = document.getElementById("form");

    form.addEventListener("submit", e => {
        e.preventDefault();

        submitButton.disabled = true;

        if (!confirmCheckbox.checked) {
            confirmLabel.classList.add("require_confirm");
            submitButton.disabled = false;
            return;
        }

        const result = window.confirm(
            "続行すると変更が確定します。息を大きく吸って、吐いて、念押しをお願いします。\nよろしいですか？"
        );

        if (!result) {
            alert("変更の送信はキャンセルされました。");
            submitButton.disabled = false;
            return;
        }

        // 開いているタブに応じて片方を未入力にする
        if (congestionLevelTab.classList.contains("active")) {
            // null相当
            waitTimeInput.value = "";
        } else if (waitTimeTab.classList.contains("active")) {
            document.getElementsByName("congestion_level").forEach(button => {
                button.checked = (button.value === "-1");
            });
        }

        submitButton.disabled = false;
        form.submit();
    });
});

function getCongestionLevel() {
    const checked = document.querySelector(
        'input[name="congestion_level"]:checked'
    );

    return checked ? checked.value : null;
}
