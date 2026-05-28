const svd = window.SVDJS;

function rotateAlignPoints(a, b) {
    if (a.length !== b.length || a.length === 0) {
        throw new Error("Point sets must have same length and cannot be empty");
    }

    const centroidA = [0, 1, 2].map(i => a.reduce((s, p) => s + p[i], 0) / a.length);
    const centroidB = [0, 1, 2].map(i => b.reduce((s, p) => s + p[i], 0) / b.length);

    const aa = a.map(p => [p[0] - centroidA[0], p[1] - centroidA[1], p[2] - centroidA[2]]);
    const bb = b.map(p => [p[0] - centroidB[0], p[1] - centroidB[1], p[2] - centroidB[2]]);

    const H = multiply(transpose(aa), bb);

    const svdH = svd.SVD(H);

    const R = multiply(svdH.v, transpose(svdH.u));

    return multiply(bb, R).map(p => [
        p[0] + centroidA[0],
        p[1] + centroidA[1],
        p[2] + centroidA[2],
    ]);
}

function multiply(a, b) {
    const aRows = a.length, aCols = a[0].length, bCols = b[0].length;
    const m = Array.from({length: aRows}, () => new Array(bCols).fill(0));
    for (let r = 0; r < aRows; r++)
        for (let c = 0; c < bCols; c++)
            for (let i = 0; i < aCols; i++)
                m[r][c] += a[r][i] * b[i][c];
            
    return m;
}

function transpose(matrix) {
    return matrix[0].map((_, i) => matrix.map(row => row[i]));
}

function centerPoints(points) {
    if (!points || points.length === 0) return points;
    
    let sumX = 0, sumY = 0, sumZ = 0;

    for (const [x, y, z] of points) {
        sumX += x;
        sumY += y;
        sumZ += z;
    }
    
    const cX = sumX / points.length;
    const cY = sumY / points.length;
    const cZ = sumZ / points.length;
        
    return points.map(([x, y, z]) => [x - cX, y - cY, z - cZ]);
}

export { rotateAlignPoints, centerPoints };
