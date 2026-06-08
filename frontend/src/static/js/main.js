import * as a from "./folding/account.js";
import * as v from "./viewer.js";
import * as foldingUI from "./folding/ui.js";

a.loadProfile();

const objectManager = v.init();
foldingUI.init(objectManager);
