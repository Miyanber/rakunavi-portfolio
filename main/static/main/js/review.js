window.addEventListener('DOMContentLoaded', () => {
    const reviewFormFixButton = document.getElementById("reviewFormFixButton");
    const reasonForm = document.getElementById("id_reason").parentElement;
    reasonForm.classList.add("reason_div");

    reviewFormFixButton.addEventListener("click", () => {
        reasonForm.classList.toggle("fixed");
    })
})