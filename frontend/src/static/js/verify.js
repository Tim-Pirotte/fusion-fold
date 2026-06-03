import { API } from "./config.js";

function init() {
    document.getElementById('complete-account').addEventListener('submit', completeAccount);
}

init();

function completeAccount(e) {
    e.preventDefault();

    const path = window.location.pathname;
    const segments = path.split('/').filter(Boolean);
    const token = segments[1];

    const password = document.getElementById('password').value;

    fetch(
        `${API}/v1/accounts/${token}`,
        {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                password,
            })
        },
    );
}
