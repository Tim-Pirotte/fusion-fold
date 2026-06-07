import { API } from "./config.js";

function init() {
    document.getElementById("reset-password")
        .addEventListener("submit", resetPassword);
}

init();

async function resetPassword(e) {
    e.preventDefault();

    const mail = document.getElementById("mail").value;

    const res = await fetch(
        `${API}/v1/accounts/password-reset`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                mail: mail,
            }),
        },
    );

    if (!res.ok) {
        alert("Something unknown went wrong");
    } else {
        alert(
            "If the e-mail is associated with an account " +
            "a reset link has been send",
        );
    }
}
