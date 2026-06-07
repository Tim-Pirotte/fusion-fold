import * as v from "./viewer.js";
import * as foldingUI from "./folding/ui.js";

const loggedIn = document.cookie
    .split("; ")
    .some(c => c.startsWith("logged_in="));

if (!loggedIn) {
    location.href = "/login";
}

const objectManager = v.init();
foldingUI.init(objectManager);
