import { API } from "./config.js";

function init() {
    document.getElementById("reset-password")
        .addEventListener("submit", completePasswordReset);
}

init();

async function completePasswordReset(e) {
    e.preventDefault();

    const path = window.location.pathname;
    const segments = path.split("/").filter(Boolean);
    const token = segments[1];

    const password = document.getElementById("password").value;

    const res = await fetch(
        `${API}/v1/accounts/password/${token}`,
        {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                password: password,
            }),
        },
    );

    if (!res.ok) {
        if (res.status === 410) {
            alert("This link has expired");
        } else if (res.status === 422) {
            alert("The account does not exist")
        } else {
            alert("Something unknown went wrong");
        }
    } else {
        location.href = "/";
    }
}
