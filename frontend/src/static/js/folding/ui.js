import * as d from "./distance_map.js";
import * as m from "./model.js";
import * as c from "./clamp.js";
import * as a from "./align.js";

const MIN_SEQUENCE_LENGTH = 2;

function init(objectManager) {
    synchronizeInputs();

    document.getElementById("sequence").addEventListener("input", validateSequence);
    document.getElementById("rna-upload").addEventListener("change", handleRnaUpload)
    document.getElementById("restore").addEventListener("click", restoreDefaultValues);
    document.getElementById("folding-form").addEventListener("submit", (e) => generateFolds(e, objectManager));
    document.getElementById("end-folding-session").addEventListener("click", hideOverview);
    
    d.init();
}

function synchronizeInputs() {
    for (const range of document.querySelectorAll("input[type='range']")) {
        const number = document.querySelector(`input[type='number'][data-sync='${range.dataset.sync}']`);

        if (!number) return;

        range.addEventListener("input", () => {
            number.value = range.value;
        });

        number.addEventListener("input", () => {
            const min = parseFloat(range.min);
            const max = parseFloat(range.max);

            let value = parseFloat(number.value);

            if (isNaN(value)) {
                value = min;
            }

            value = c.clamp(value, min, max);

            number.value = value;
            range.value = value;
        });
    }
}

function validateSequence() {
    const $sequence = document.getElementById("sequence");
    let message = "";

    if ($sequence.value.length < MIN_SEQUENCE_LENGTH) {
        message = `The sequence should be at least ${MIN_SEQUENCE_LENGTH} nucleotides long`;
    } else if (!/^[AUGCaugc\s]*$/.test($sequence.value)) {
        message = "Only A, C, G and U are allowed";
    }

    $sequence.setCustomValidity(message);
    $sequence.reportValidity();
}

async function handleRnaUpload(e) {
    const file = e.currentTarget.files[0];

    if (!file) return;

    try {
        const text = await file.text();
        const data = JSON.parse(text);

        if (data["name"]) {
            document.getElementById("name").value = data["name"];
        }

        if (data["sequence"]) {
            if (data["sequence"].length > 1024) {
                alert("Sequence length should be smaller than 1024");

                return;
            }

            document.getElementById("sequence").value = data["sequence"];
        }

        if (data["ground_truth_coords"]) {
            window.groundTruthCoords = a.centerPoints(data["ground_truth_coords"]);

            console.info("Ground truth coordinates loaded successfully.");
        }
    } catch (err) {
        console.error(err);
        alert("Invalid .rna file")

        return;
    }
}

function restoreDefaultValues(e) {
    e.preventDefault();

    document.querySelectorAll("[data-sync='folds']").forEach($f => $f.value = 3);
    document.querySelectorAll("[data-sync='steps']").forEach($s => $s.value = 3);
    document.getElementById("return-noise").value = "false";
}

// The EventSource will raise the error event on a reload
let isNavigating = false;
window.addEventListener('beforeunload', _ => isNavigating = true);

async function generateFolds(e, objectManager) {
    e.preventDefault();

    showOverview();

    const sequence = document.getElementById("sequence").value.replaceAll(" ", "").toUpperCase();
    const folds = document.getElementById("folds").value;
    const steps = document.getElementById("steps").value;
    const returnNoise = document.getElementById("return-noise").value === "true";
    const sessionId = await getFoldingSession(sequence, folds, steps, returnNoise);

    if (sessionId === null) {
        hideOverview();

        return;
    }

    const reference = m.createStrand(objectManager, sequence, -1, document.getElementById("name").value);
    reference.addFrame(window.groundTruthCoords);

    let lastStrand = null;
    let lastDistanceMap = null;

    const eventSource = new EventSource(`/api/stream-folding/${sessionId}`);

    eventSource.onmessage = (e) => {
        const data = JSON.parse(e.data);
        const { fold, step, coords } = data;

        updateProgressBar(fold, step, folds, steps);

        if (!lastStrand || lastStrand.fold !== fold) {
            if (lastStrand) {
                objectManager.setObjectVisibility(lastStrand.object, false)
            }

            lastStrand = m.createStrand(
                objectManager, 
                sequence, 
                fold, 
                `${document.getElementById("name").value} #${fold + 1}`,
            );

            lastDistanceMap = d.MapNavigator.addMap(sequence.length);
        }

        d.updateDistanceMap(
            lastDistanceMap, 
            coords, 
            sequence.length,
        );

        lastStrand.addFrame(a.rotateAlignPoints(window.groundTruthCoords, coords));
    };

    eventSource.addEventListener("end", function() {
        console.info("Stream finished successfully");
        eventSource.close();
        changeToBackButton();
    });

    eventSource.addEventListener("error", function(e) {
        if (isNavigating) {
            console.info("Stream closed due to page navigation");
            
            return;
        }

        console.error("Stream failed");
        eventSource.close();
        alert("Something went wrong while streaming");
        changeToBackButton();
    });

    const $overview = document.getElementById('folding-overview');

    $overview.addEventListener("folding-session-ended", function() {
        console.info("Stream canceled");
        eventSource.close();
    }, { once: true });
}

function showOverview() {
    const $form = document.getElementById("folding-form");
    $form.style.display = "none";

    const $backButton = document.getElementById("end-folding-session");
    $backButton.textContent = "Cancel";
    $backButton.classList.add("cancel");

    d.MapNavigator.clear();

    const $progressBar = document.getElementById("progress-bar");
    $progressBar.classList.remove("finished");
    $progressBar.style.width = "";

    const $overview = document.getElementById('folding-overview');

    $overview.querySelector("h2").textContent = document.getElementById("name").value;
    $overview.style.display = "flex";
}

function hideOverview() {
    const $overview = document.getElementById('folding-overview');
    $overview.style.display = "";

    const $form = document.getElementById("folding-form");
    $form.style.display = "";

    $overview.dispatchEvent(new CustomEvent("folding-session-ended"));
}

async function getFoldingSession(sequence, folds, steps, returnNoise) {
    const res = await fetch(
        "/api/generate-folding-session/", 
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                sequence: sequence,
                folds_to_generate: folds,
                steps_per_fold: steps,
                return_noise: returnNoise,
            })
        },
    );

    if (!res.ok) {
        alert("Something went wrong while generating a new folding session.");

        return null;
    }

    const data = await res.json();

    return data.sessionId;
}

function updateProgressBar(fold, step, totalFolds, totalSteps) {
    const $progressBar = document.getElementById("progress-bar");

    const completed = (fold * totalSteps) + (step + 1);
    const total = totalFolds * totalSteps;
    const progress = (completed / total) * 100;
    
    $progressBar.style.width = `${progress}%`;

    if (completed >= total) {
        $progressBar.classList.add("finished");
    }
}

function changeToBackButton() {
    const $backButton = document.getElementById("end-folding-session");
    $backButton.textContent = "Back";
    $backButton.classList.remove("cancel");
}

export { init };
