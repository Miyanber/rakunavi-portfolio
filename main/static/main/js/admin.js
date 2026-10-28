document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("#content-main form");
    form.addEventListener("submit", async e => {
        e.preventDefault();
        form.submit();
    })
})