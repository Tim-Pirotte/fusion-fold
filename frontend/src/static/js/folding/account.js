import { API } from "../config.js";

async function init(sidePanel) {
    const loggedIn = document.cookie
        .split("; ")
        .some(c => c.startsWith("logged_in="));

    if (!loggedIn) {
        location.href = "/login";
    }

    sidePanel.addPanel("account-dashboard");

    document.getElementById("show-account")
        .addEventListener("click", (e) => toggleDashBoard(e, sidePanel));

    await loadProfile();
}

async function loadProfile() {
    let res;

    try {
        res = await fetch(
            `${API}/v1/accounts`,
            {
                method: "GET",
                credentials: "include",
            },
        );
    } catch (e) {
        console.error(e);
        document.getElementById("display-name").textContent = "Error";
        document.getElementById("dashboard-display-name").textContent = "Error";
        document.getElementById("display-name-input").value = "Error";

        return;
    }

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

    document.getElementById("display-name").textContent = data["display_name"];
    document.getElementById("dashboard-display-name").textContent = data["display_name"];
    document.getElementById("display-name-input").value = data["display_name"];
}

function toggleDashBoard(e, sidePanel) {
    const $button = e.currentTarget;

    if ($button.hasAttribute("data-show-account")) {
        sidePanel.showPanel("account-dashboard");
    } else {
        sidePanel.back();
    }

    $button.toggleAttribute("data-show-account")
}

export { init };
