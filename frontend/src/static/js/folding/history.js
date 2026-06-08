import { API } from "../config.js";

function init(sidePanel) {
    sidePanel.addPanel("history");

    document.getElementById("show-history")
        .addEventListener("click", (_) => toggleHistory(sidePanel));

    document.getElementById("history")
        .addEventListener("click", (e) => handleHistoryClick(e, sidePanel))
}

function toggleHistory(sidePanel) {
    if (sidePanel.getCurrentPanel() !== "history") {
        sidePanel.showPanel("history");
        renderHistory();
    } else {
        sidePanel.back();
    }
}

async function renderHistory() {
    let res;

    try {
        res = await fetch(
            `${API}/v1/predictions`,
            {
                method: "GET",
                credentials: "include",
            },
        );
    } catch (e) {
        console.error(e);
        alert("Something unknown went wrong");

        return;
    }

    if (!res.ok) {
        if (res.status === 404) {
            alert("The logged in account does not exist anymore");

            return;
        } else if (res.status === 401) {
            location.href = "/login";
        } else {
            alert("Something went wrong while retrieving history data");

            return;
        }
    }

    const data = await res.json();

    const $template = document.getElementById("prediction-template");
    const $history = document.getElementById("history");

    $history.querySelectorAll(":scope > :not(template)")
        .forEach(el => el.remove());

    for (const prediction of data.predictions) {
        const date = new Date(prediction.created_at);

        const formatted = date.toLocaleString(undefined, {
            dateStyle: 'medium',
            timeStyle: 'short',
            timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        });

        const $li = $template.content.cloneNode(true).querySelector("li");

        $li.dataset.id = prediction["id"];
        $li.querySelector("span").textContent = `${formatted} ${prediction["display_name"]}`;

        $history.appendChild($li);
    }
}

function handleHistoryClick(e, sidePanel) {
    const button = e.target.closest("button");

    if (!button) {
        return;
    }

    const id = button.closest("li").dataset.id;

    if (button.classList.contains("load-sequence")) {
        loadSequence(id);
        sidePanel.back();
    } else {
        loadCoordss(id);
    }
}

async function loadSequence(id) {
    let res;

    try {
        res = await fetch(
            `${API}/v1/predictions/${id}/sequence`,
            {
                method: "GET",
                credentials: "include",
            },
        );
    } catch (e) {
        console.error(e);
        alert("Something unknown went wrong");

        return;
    }

    if (!res.ok) {
        if (res.status === 404) {
            alert("The logged in account does not exist anymore");

            return;
        } else if (res.status === 401) {
            location.href = "/login";
        } else {
            alert("Something went wrong while retrieving history data");

            return;
        }
    }

    const data = await res.json();

    document.getElementById("sequence").value = data["sequence"];
}

async function loadCoordss(id) {

}

export { init };
