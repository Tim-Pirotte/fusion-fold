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

    let res;

    try {
        res = await fetch(
            `${API}/v1/accounts/login`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                credentials: "include",
                body: JSON.stringify({
                    mail: mail,
                    password: password,
                }),
            },
        );
    } catch (e) {
        console.error(e);
        alert("Could not connect to the server. Please try again later.");

        return
    }

    if (!res.ok) {
        if (res.status === 400) {
            alert("Incorrect e-mail and/or password");
        } else {
            alert("Something unknown went wrong");
        }
    } else {
        location.href = "/";
    }
}

async function register(e) {
    e.preventDefault();

    const mail = document.getElementById("email").value;
    const displayName = document.getElementById("display-name").value;

    const res = await fetch(
        `${API}/v1/accounts`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            credentials: "include",
            body: JSON.stringify({
                mail: mail,
                display_name: displayName,
            }),
        },
    );

    if (!res.ok) {
        if (res.status === 403) {
            alert("An account is already registered for this e-mail");
        } else {
            alert("Something unknown went wrong");
        }
    } else {
        alert(
            "Account successfully created. " +
            "Please check your e-mail for verification.",
        )
    }
}
