import { API } from "../config.js";

async function loadProfile() {
    const loggedIn = document.cookie
        .split("; ")
        .some(c => c.startsWith("logged_in="));

    if (!loggedIn) {
        location.href = "/login";
    }

    const res = await fetch(
        `${API}/accounts/`,
    );
}

export { loadProfile };
