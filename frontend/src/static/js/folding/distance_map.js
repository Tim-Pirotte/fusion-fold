const DISTANCE_MAP_LUT = (() => {
    const stops = [
        [68, 1, 84],
        [72, 35, 116],
        [42, 120, 142],
        [34, 168, 132],
        [122, 209, 81],
        [253, 231, 37],
    ];

    const lut = new Uint8Array(256 * 3);

    for (let i = 0; i < 256; i++) {
        const t = i / 255;
        const segment = t * (stops.length - 1);
        const low = Math.floor(segment);
        const high = Math.ceil(segment);
        const localT = segment - low;

        const c1 = stops[low];
        const c2 = stops[high];

        lut[i * 3]     = c1[0] + (c2[0] - c1[0]) * localT; // R
        lut[i * 3 + 1] = c1[1] + (c2[1] - c1[1]) * localT; // G
        lut[i * 3 + 2] = c1[2] + (c2[2] - c1[2]) * localT; // B
    }

    return lut;
})();

function init() {
    document.getElementById("next-distance-map").addEventListener("click", MapNavigator.next);
    document.getElementById("previous-distance-map").addEventListener("click", MapNavigator.prev);
}

function updateDistanceMap(distanceMap, coords) {
    const size = distanceMap.canvas.width;

    if (size !== distanceMap.canvas.height) {
        console.warn("Expects canvas to be square");
    }

    const imageData = distanceMap.createImageData(size, size);
    const data = imageData.data;

    const distances = new Float32Array(size * size);

    let min = Infinity;
    let max = -Infinity;

    const gt = window.groundTruthCoords;

    for (let i = 0; i < size; i++) {
        for (let j = 0; j < size; j++) {
            let dist;
            
            if (j >= i) {
                const dx = coords[i][0] - coords[j][0];
                const dy = coords[i][1] - coords[j][1];
                const dz = coords[i][2] - coords[j][2];
                
                dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
            } else if (gt && gt[i] && gt[j]) {
                const dx = gt[i][0] - gt[j][0];
                const dy = gt[i][1] - gt[j][1];
                const dz = gt[i][2] - gt[j][2];

                dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
            }

            if (dist !== undefined) {
                distances[i * size + j] = dist;

                if (dist < min) min = dist;
                if (dist > max) max = dist;
            }
        }
    }

    const range = max - min;

    for (let i = 0; i < size; i++) {
        for (let j = 0; j < size; j++) {
            const index = (i * size + j) * 4;
            const dist = distances[i * size + j];

            if (dist !== undefined || j >= i) {
                const val = range === 0 ? 0 : ((dist - min) / range) * 255;
                const lutIndex = Math.floor(Math.max(0, Math.min(255, val))) * 3;

                data[index]     = DISTANCE_MAP_LUT[lutIndex];     // R
                data[index + 1] = DISTANCE_MAP_LUT[lutIndex + 1]; // G
                data[index + 2] = DISTANCE_MAP_LUT[lutIndex + 2]; // B
                data[index + 3] = 255;                            // A
            } else {
                data[index + 3] = 0;                              // A
            }
        }
    }

    distanceMap.putImageData(imageData, 0, 0);
}

const MapNavigator = {
    currentIndex: 0,
    maps: [], 

    updateDisplay() {
        const counter = document.getElementById("distance-map-counter");

        for (const [i, canvas] of MapNavigator.maps.entries()) {
            canvas.classList.toggle("active", i === MapNavigator.currentIndex);
        }

        if (MapNavigator.maps.length > 0) {
            counter.textContent = `${MapNavigator.currentIndex + 1} / ${MapNavigator.maps.length}`;
        }
    },

    addMap(size) {
        const $template = document.getElementById("distance-map-template");
        const $distanceMap = $template.content.cloneNode(true).querySelector("canvas");

        $distanceMap.width = size;
        $distanceMap.height = size;

        const $distanceMaps = document.getElementById("distance-maps");
        $distanceMaps.appendChild($distanceMap);

        MapNavigator.maps.push($distanceMap);
        MapNavigator.currentIndex = MapNavigator.maps.length - 1;
        MapNavigator.updateDisplay();

        return $distanceMap.getContext("2d");
    },

    next() {
        if (MapNavigator.maps.length === 0) return;

        MapNavigator.currentIndex = (MapNavigator.currentIndex + 1) % MapNavigator.maps.length;
        MapNavigator.updateDisplay();
    },

    prev() {
        if (MapNavigator.maps.length === 0) return;

        MapNavigator.currentIndex = (MapNavigator.currentIndex - 1 + MapNavigator.maps.length) % MapNavigator.maps.length;
        MapNavigator.updateDisplay();
    },
    
    clear() {
        MapNavigator.maps = [];
        MapNavigator.currentIndex = 0;

        const $distanceMaps = document.getElementById("distance-maps").querySelectorAll(".distance-map");
    
        for (const $distanceMap of $distanceMaps) {
            $distanceMap.remove();
        }
        
        MapNavigator.updateDisplay();
    }
};

export { init, updateDistanceMap, MapNavigator };
