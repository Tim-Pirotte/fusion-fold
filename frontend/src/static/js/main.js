import * as a from "./folding/account.js";
import * as v from "./viewer.js";
import * as s from "./folding/side_panel.js";
import * as h from "./folding/history.js";
import * as foldingUI from "./folding/ui.js";

const sidePanel = s.SidePanel;
a.init(sidePanel);
h.init(sidePanel);

const objectManager = v.init();
foldingUI.init(objectManager, sidePanel);
