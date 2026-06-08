import { API } from "../config.js";

async function loadProfile() {
    const loggedIn = document.cookie
        .split("; ")
        .some(c => c.startsWith("logged_in="));

    if (!loggedIn) {
        location.href = "/login";
    }

    const res = await fetch(
        `${API}/v1/accounts`,
        {
            method: "GET",
            credentials: "include",
        },
    );

    if (!res.ok) {
        if (res.status === 404) {
            alert("The logged in account does not exist anymore");
            return;
        } else if (res.status === 401) {
            location.href = "/login";
        } else {
            alert("Something went wrong while retrieving account data");
            return;
        }
    }

    const data = await res.json();

    document.getElementById("display-name").innerText = data["display_name"];
}

export { loadProfile };
