import { API } from "./config.js";

function init() {
    document.getElementById("complete-account")
        .addEventListener("submit", completeAccount);
}

init();

async function completeAccount(e) {
    e.preventDefault();

    const path = window.location.pathname;
    const segments = path.split("/").filter(Boolean);
    const token = segments[1];

    const password = document.getElementById("password").value;

    const res = await fetch(
        `${API}/v1/accounts/${token}`,
        {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json",
            },
            credentials: "include",
            body: JSON.stringify({
                password,
            }),
        },
    );

    if (!res.ok) {
        if (res.status === 410) {
            alert("This verification link has expired");
        } else if (res.status === 403) {
            alert("The account does not exist or has already been verified");
        } else {
            alert("Something unknown went wrong");
        }
    } else {
        location.href = "/";
    }
}
