import { API } from "./config.js";

function init() {
    document.querySelectorAll("input[name='toggle']")
        .forEach($i => $i.addEventListener("change", toggleForm));

    document.getElementById("login").addEventListener("submit", login);
    document.getElementById("register").addEventListener("submit", register);
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

async function login(e) {
    e.preventDefault();

    const mail = document.getElementById("mail").value;
    const password = document.getElementById("password").value;

    const res = await fetch(
        `${API}/v1/accounts/login`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                mail: mail,
                password: password,
            }),
        },
    );

    if (!res.ok) {
        alert("Incorrect e-mail and/or password");
    } else {
        location.href = "/";
    }
}

function register(e) {
    e.preventDefault();
}
