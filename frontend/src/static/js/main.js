import * as a from "./folding/account.js";
import * as v from "./viewer.js";
import * as s from "./folding/side_panel.js";
import * as h from "./folding/history.js";
import * as foldingUI from "./folding/ui.js";

const sidePanel = s.SidePanel;
a.init(sidePanel);

const objectManager = v.init();
h.init(objectManager, sidePanel);
foldingUI.init(objectManager, sidePanel);
