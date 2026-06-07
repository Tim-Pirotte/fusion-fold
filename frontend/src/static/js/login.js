function init() {
    document.querySelectorAll("input[name='toggle']")
        .forEach($i => $i.addEventListener("change", toggleForm));
}

init();

function toggleForm() {
    const $login = document.getElementById("login");
    const $register = document.getElementById("register");

    if (document.getElementById("login-toggle").checked) {
        $login.classList.remove("hidden");
        $register.classList.add("hidden");
    } else {
        $login.classList.add("hidden");
        $register.classList.remove("hidden");
    }
}
