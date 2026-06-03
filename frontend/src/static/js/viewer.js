import * as t from "./lib/three.js";
import { OrbitControls } from './lib/OrbitControls.js';

const COLOR_PALETTE = [
    "#fc0303", 
    "#fc8c03", 
    "#ebfc03", 
    "#03fc41", 
    "#03fcc6", 
    "#03c6fc",
    "#9003fc",
    "#fc036b",
]

function init() {
    const container = document.querySelector("main");
    const scene = new t.Scene();
    const camera = getCamera(container);
    const renderer = new t.WebGLRenderer({ antialias: true });

    loadBackground(scene);
    loadControls(camera, renderer);
    loadResizing(window, container, camera, renderer);

    container.appendChild(renderer.domElement);

    startRenderLoop(renderer, scene, camera);

    return getObjectManager(scene);
}

function getCamera(container) {
    const camera = new t.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.z = 5;

    return camera;
}

function loadBackground(scene) {
    new t.TextureLoader().load("./static/images/background.webp", (texture) => {
        texture.mapping = t.EquirectangularReflectionMapping;

        scene.background = texture;
        scene.environment = texture;
    });
}

function loadControls(camera, renderer) {
    new OrbitControls(camera, renderer.domElement);
}

function loadResizing(window, container, camera, renderer) {
    function resize() {
        const width = container.clientWidth;
        const height = container.clientHeight;

        renderer.setSize(width, height, false);

        camera.aspect = width / height;
        camera.updateProjectionMatrix();
    }

    window.addEventListener("resize", resize);
    resize();
}

function startRenderLoop(renderer, scene, camera) {
    renderer.setAnimationLoop(_ => renderer.render(scene, camera));
}

function getObjectManager(scene) {
    return { scene, addObject, setObjectVisibility, objectCount: 0 };
}

function addObject(objectManager, mesh, name, onColorChange) {
    objectManager.scene.add(mesh);

    const $objects = document.getElementById("objects");
    const $template = document.getElementById("object");
    const $object = $template.content.cloneNode(true);

    const color = COLOR_PALETTE[objectManager.objectCount % COLOR_PALETTE.length];
    const $colorInput = $object.querySelector(".color");
    $colorInput.value = color;

    if (onColorChange) onColorChange(color);

    $colorInput.addEventListener("input", (e) => {
        if (onColorChange) {
            onColorChange(e.currentTarget.value);
        } else if (mesh.material) {
            mesh.material.color.set(e.currentTarget.value);
        }
    });

    if (!mesh.material && !onColorChange) {
        $colorInput.remove();
    }

    if (name) {
        $object.querySelector(".name").value = name;
    }

    const $visible = $object.querySelector(".visible");
    const object = { mesh, $visible };

    $visible.addEventListener("change", _ => setObjectVisibility(object, $visible.checked));

    $object.querySelector("button").addEventListener("click", (e) => {
        objectManager.scene.remove(mesh);
        e.currentTarget.closest("li").remove();

        if (mesh.geometry) {
            mesh.geometry.dispose();
        }
        
        if (mesh.material) {
            if (Array.isArray(mesh.material)) {
                mesh.material.forEach(m => m.dispose());
            } else {
                mesh.material.dispose();
            }
        }
    });

    $objects.appendChild($object);
    objectManager.objectCount++

    return { mesh, $visible };
}

function setObjectVisibility(object, visible) {
    object.mesh.visible = visible;
    object.$visible.checked = visible;
}

export { init };
