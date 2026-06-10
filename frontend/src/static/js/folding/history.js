import { API } from "../config.js";
import * as m from "./model.js";

function init(objectManager, sidePanel) {
    sidePanel.addPanel("history");

    document.getElementById("show-history")
        .addEventListener("click", (_) => toggleHistory(sidePanel));

    document.getElementById("history")
        .addEventListener("click", (e) => handleHistoryClick(e, objectManager, sidePanel))
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

function handleHistoryClick(e, objectManager, sidePanel) {
    const button = e.target.closest("button");

    if (!button) {
        return;
    }

    const $li = button.closest("li");
    const id = $li.dataset.id;

    if (button.classList.contains("load-sequence")) {
        loadSequence(id);
        sidePanel.back();
    } else {
        loadCoords(objectManager, id, $li.querySelector("span").textContent);
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
            alert("Something went wrong while retrieving the sequence");

            return;
        }
    }

    const data = await res.json();

    document.getElementById("sequence").value = data["sequence"];
    window.groundTruthCoords = null;
}

async function loadCoords(objectManager, id, name) {
    let res;

    try {
        res = await fetch(
            `${API}/v1/predictions/${id}/coords`,
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
            alert("Something went wrong while retrieving the coordinates");

            return;
        }
    }

    const data = await res.json();
    const coords = data.coords.map(({ x, y, z }) => [x, y, z]);

    // TODO: this should use the actual sequence but I don't have enough time to do that
    const strand = m.createStrand(objectManager, "A".repeat(coords.length), -1, name);
    strand.addFrame(coords);
}

export { init };
