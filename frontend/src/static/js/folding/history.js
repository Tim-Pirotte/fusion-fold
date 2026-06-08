function init(sidePanel) {
    sidePanel.addPanel("history");

    document.getElementById("show-history")
        .addEventListener("click", (_) => toggleHistory(sidePanel));
}

function toggleHistory(sidePanel) {
    if (sidePanel.getCurrentPanel() !== "history") {
        sidePanel.showPanel("history");
    } else {
        sidePanel.back();
    }
}

export { init };
