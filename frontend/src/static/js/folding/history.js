import { API } from "../config.js";

function init(sidePanel) {
    sidePanel.addPanel("history");

    document.getElementById("show-history")
        .addEventListener("click", (_) => toggleHistory(sidePanel));
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

    for (const prediction of data.predictions) {
        const $li = $template.content.cloneNode(true).querySelector("li");

        $history.appendChild($li);
    }
}

export { init };
