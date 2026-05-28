import * as t from "../lib/three.js";

import * as c from "./clamp.js";

const NUCLEOTIDES_BRIGHTNESS_OFFSETS = {
    'A': 0.15,
    'U': -0.15,
    'C': 0.30,
    'G': -0.30,
};

const CURVE_BRIGHTNESS_OFFSET = 0.05;

const NUCLEOTIDE_DIAMETER = 0.8;
const NUCLEOTIDE_RESOLUTION = 12;

const CURVE_DIAMETER = 0.2;
const CURVE_RESOLUTION = 8;
const CURVE_RADIAL_SEGMENTS = 8;

const ANIMATION_DURATION_MS = 1_500;

function createStrand(objectManager, sequence, fold, name) {
    const strandGroup = new t.Group();
    const nucleotideMeshes = [];
    const nucleotideGeometry = new t.SphereGeometry(
        NUCLEOTIDE_DIAMETER, NUCLEOTIDE_RESOLUTION, NUCLEOTIDE_RESOLUTION,
    );

    for (const nucleotide of sequence) {
        const nucleotideMesh = new t.Mesh(
            nucleotideGeometry, 
            new t.MeshStandardMaterial({
                roughness: 0,
            })
        );
        
        nucleotideMesh.userData.baseType = nucleotide;
        
        strandGroup.add(nucleotideMesh);
        nucleotideMeshes.push(nucleotideMesh);
    }

    const points = nucleotideMeshes.map(m => m.position.clone());
    const curve = new t.CatmullRomCurve3(points);

    const tubeGeometry = new t.TubeGeometry(
        curve, sequence.length * CURVE_RESOLUTION, CURVE_DIAMETER, CURVE_RADIAL_SEGMENTS,
    );

    const tubeMaterial = new t.MeshPhysicalMaterial({
        color: 0xffffff,
        roughness: 0,
        transmission: 1,
        thickness: 0.5,
        transparent: true,
        opacity: 0.9,
        ior: 1.5,
        envMapIntensity: 1.0,
    });

    const backbone = new t.Mesh(tubeGeometry, tubeMaterial);
    backbone.userData.curve = curve;

    strandGroup.add(backbone);

    const object = objectManager.addObject(
        objectManager, 
        strandGroup, 
        name, 
        (c) => colorSequence(nucleotideMeshes, backbone, c),
    );

    return {
        fold,
        object,
        nucleotideMeshes,
        backbone,
        animationQueue: [],
        isAnimating: false,

        addFrame(coords) {
            this.animationQueue.push(coords);
        
            if (!this.isAnimating) {
                this.isAnimating = true;
                processAnimationQueue(this);
            }
        }
    };
}

const _hsl = { h: 0, s: 0, l: 0 };

function colorSequence(nucleotideMeshes, backbone, color) {
    const themeColor = new t.Color(color);
    themeColor.getHSL(_hsl);
    
    const baseH = _hsl.h;
    const baseS = _hsl.s;
    const baseL = _hsl.l;

    const backboneLightness = Math.min(1, baseL + CURVE_BRIGHTNESS_OFFSET); 
    backbone.material.color.setHSL(baseH, baseS, backboneLightness);

    for (const mesh of nucleotideMeshes) {
        const offset = NUCLEOTIDES_BRIGHTNESS_OFFSETS[mesh.userData.baseType] || 0;

        mesh.material.color.setHSL(
            baseH, 
            baseS,
            c.clamp(baseL + offset, 0, 1),
        );
    }
}

const _tempVec = new t.Vector3();

async function processAnimationQueue(strand) {
    if (strand.animationQueue.length === 0) {
        strand.isAnimating = false;
        
        return;
    }

    const startCoords = strand.nucleotideMeshes.map(m => m.position.clone());
    const targetCoords = strand.animationQueue.shift();

    const startTime = performance.now();

    function animateStep(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / ANIMATION_DURATION_MS, 1);

        const curvePoints = strand.backbone.userData.curve.points;

        for (const [i, nucleotide] of strand.nucleotideMeshes.entries()) {
            const start = startCoords[i];
            const end = targetCoords[i];

            _tempVec.set(end[0], end[1], end[2]);

            nucleotide.position.lerpVectors(start, _tempVec, progress);
            curvePoints[i].copy(nucleotide.position);
        }

        updateBackbone(strand.backbone);

        if (progress < 1) {
            requestAnimationFrame(animateStep);
        } else {
            processAnimationQueue(strand);
        }
    }

    requestAnimationFrame(animateStep);
}

function updateBackbone(backbone) {    
    backbone.userData.curve.updateArcLengths();
    backbone.geometry.dispose();    
    backbone.geometry = new t.TubeGeometry(
        backbone.userData.curve, 
        backbone.userData.curve.points.length * CURVE_RESOLUTION, 
        CURVE_DIAMETER, 
        CURVE_RADIAL_SEGMENTS, 
        false
    );
}

export { createStrand, processAnimationQueue };
