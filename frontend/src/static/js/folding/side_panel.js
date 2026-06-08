const SidePanel = {
    panels: [],
    panelStack: [],

    addPanel(id) {
        const $panel = document.getElementById(id);

        if (!$panel) {
            console.error(`There is no panel with the id '${id}'`);

            return;
        }

        $panel.classList.add("hide");

        this.panels.push(id);
    },

    showPanel(id) {
        if (!this.panels.includes(id)) {
            console.error(`There is no panel with the id '${id}' to show`);

            return;
        }

        for (const panel of this.panels) {
            document.getElementById(panel)
                .classList.toggle("hide", panel !== id);
        }

        this.panelStack.push(id);
    },

    back() {
        if (this.panelStack.length >= 2) {
            this.panelStack.pop();
            this.showPanel(this.panelStack.at(-1));
        }
    }
}

export { SidePanel };
