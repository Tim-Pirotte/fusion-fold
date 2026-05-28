import * as v from "./viewer.js";
import * as foldingUI from "./folding/ui.js";

const objectManager = v.init();
foldingUI.init(objectManager);
