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
        .addEventListener("click", (_) => toggleDashBoard(sidePanel));

    document.getElementById("log-out")
        .addEventListener("click", logOut);

    document.getElementById("delete-account")
        .addEventListener("click", deleteAccount);

    document.getElementById("change-display-name")
        .addEventListener("submit", changeDisplayName);

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
        setDisplayName("Error");

        return;
    }

    if (!res.ok) {
        if (res.status === 404) {
            alert("The logged in account does not exist anymore");
            setDisplayName("Error");

            return;
        } else if (res.status === 401) {
            location.href = "/login";
        } else {
            alert("Something went wrong while retrieving account data");
            setDisplayName("Error");

            return;
        }
    }

    const data = await res.json();

    setDisplayName(data["display_name"]);
}

function setDisplayName(name) {
    document.getElementById("display-name").textContent = name;
    document.getElementById("dashboard-display-name").textContent = name;
    document.getElementById("display-name-input").value = name;
}

function toggleDashBoard(sidePanel) {
    if (sidePanel.getCurrentPanel() !== "account-dashboard") {
        sidePanel.showPanel("account-dashboard");
    } else {
        sidePanel.back();
    }
}

async function logOut() {
    if (!window.confirm("Are you sure that you want to log out?")) {
        return;
    }

    const res = await fetch(
        `${API}/v1/accounts/logout`,
        {
            method: "POST",
            credentials: "include",
        },
    );

    if (!res.ok) {
        alert("Something went wrong while logging out");

        return;
    }

    location.href = "/login";
}

async function deleteAccount() {
    if (!window.confirm(
        "Are you sure that you want to DELETE your account? " +
        "This action CANNOT be undone.",
    )) {
        return;
    }

    const res = await fetch(
        `${API}/v1/accounts`,
        {
            method: "DELETE",
            credentials: "include",
        },
    );

    if (!res.ok) {
        if (res.status === 401) {
            logOut();

            return;
        } else if (res.status === 404) {
            alert("The account you are trying to delete does not exist");

            return;
        } else {
            alert("Something went wrong while deleting the account");

            return;
        }
    }

    location.href = "/login";
}

async function changeDisplayName(e) {
    e.preventDefault();

    const displayName = document.getElementById("display-name-input").value;

    let res;

    try {
        res = await fetch(
            `${API}/v1/accounts/display-name`,
            {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                },
                credentials: "include",
                body: JSON.stringify({
                    display_name: displayName,
                }),
            },
        );
    } catch (e) {
        console.error(e);
        loadProfile();

        return;
    }

    if (!res.ok) {
        if (res.status === 404) {
            alert("The logged in account does not exist anymore");
        } else if (res.status === 401) {
            location.href = "/login";
        } else {
            alert("Something unknown went wrong");
        }
    }

    loadProfile();
}

export { init };
