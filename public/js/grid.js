import * as THREE from 'three';

export class GridRenderer {
    constructor(scene) {
        this.scene = scene;
        this.group = new THREE.Group();
        this.scene.add(this.group);

        this.obstacleGroup = new THREE.Group();
        this.group.add(this.obstacleGroup);

        this.markerGroup = new THREE.Group();
        this.group.add(this.markerGroup);

        this.launchPadMesh = null;
        this.clickableGround = null;
        this.obstacles = new Set();
        this.onObstacleToggle = null;

        this.pathGroup = new THREE.Group();
        this.group.add(this.pathGroup);

        this.width = 20;
        this.height = 20;
    }

    build(width, height, obstacles, packages) {
        this.width = width;
        this.height = height;
        this.obstacles = new Set(obstacles.map(([x, y]) => `${x},${y}`));

        // Clear previous
        this.group.remove(this.obstacleGroup);
        this.obstacleGroup = new THREE.Group();
        this.group.add(this.obstacleGroup);

        this.group.remove(this.markerGroup);
        this.markerGroup = new THREE.Group();
        this.group.add(this.markerGroup);

        if (this.launchPadMesh) {
            this.group.remove(this.launchPadMesh);
        }
        if (this.clickableGround) {
            this.group.remove(this.clickableGround);
        }

        // Ground plane
        const groundGeo = new THREE.PlaneGeometry(width, height);
        const groundMat = new THREE.MeshStandardMaterial({
            color: 0x1a1a2a,
            roughness: 0.9,
            metalness: 0.1,
        });
        const ground = new THREE.Mesh(groundGeo, groundMat);
        ground.rotation.x = -Math.PI / 2;
        ground.position.set(width / 2 - 0.5, -0.01, height / 2 - 0.5);
        ground.receiveShadow = true;
        this.group.add(ground);
        this.clickableGround = ground;

        // Grid lines
        const gridHelper = new THREE.GridHelper(Math.max(width, height), Math.max(width, height), 0x333355, 0x222244);
        gridHelper.position.set(width / 2 - 0.5, 0, height / 2 - 0.5);
        this.group.add(gridHelper);

        // Launch pad
        const padGeo = new THREE.CylinderGeometry(0.4, 0.4, 0.05, 32);
        const padMat = new THREE.MeshStandardMaterial({
            color: 0x00ff88,
            emissive: 0x00ff88,
            emissiveIntensity: 0.5,
        });
        this.launchPadMesh = new THREE.Mesh(padGeo, padMat);
        this.launchPadMesh.position.set(0, 0.03, 0);
        this.launchPadMesh.receiveShadow = true;
        this.group.add(this.launchPadMesh);

        // Obstacles
        this._renderObstacles();

        // Package destinations
        this._renderPackageMarkers(packages);
    }

    _renderObstacles() {
        // Clear
        while (this.obstacleGroup.children.length) {
            this.obstacleGroup.remove(this.obstacleGroup.children[0]);
        }

        const obsMat = new THREE.MeshStandardMaterial({
            color: 0x444466,
            roughness: 0.7,
            metalness: 0.3,
        });

        for (const key of this.obstacles) {
            const [x, y] = key.split(',').map(Number);
            const obsGeo = new THREE.BoxGeometry(0.9, 0.6, 0.9);
            const cube = new THREE.Mesh(obsGeo, obsMat);
            cube.position.set(x, 0.3, y);
            cube.castShadow = true;
            cube.receiveShadow = true;
            this.obstacleGroup.add(cube);
        }
    }

    _renderPackageMarkers(packages) {
        while (this.markerGroup.children.length) {
            this.markerGroup.remove(this.markerGroup.children[0]);
        }

        const colors = [0x00d4ff, 0xff6644, 0xffdd00, 0xff44ff, 0x44ff44, 0xff8800];

        packages.forEach((pkg, i) => {
            const [x, y] = pkg.destination;
            const color = colors[i % colors.length];

            // Pin base
            const baseGeo = new THREE.CylinderGeometry(0.3, 0.3, 0.05, 16);
            const baseMat = new THREE.MeshStandardMaterial({
                color,
                emissive: color,
                emissiveIntensity: 0.3,
            });
            const base = new THREE.Mesh(baseGeo, baseMat);
            base.position.set(x, 0.03, y);
            this.markerGroup.add(base);

            // Pin pole
            const poleGeo = new THREE.CylinderGeometry(0.03, 0.03, 0.8, 8);
            const poleMat = new THREE.MeshStandardMaterial({ color });
            const pole = new THREE.Mesh(poleGeo, poleMat);
            pole.position.set(x, 0.4, y);
            this.markerGroup.add(pole);

            // Pin top sphere
            const sphereGeo = new THREE.SphereGeometry(0.1, 16, 16);
            const sphere = new THREE.Mesh(sphereGeo, baseMat);
            sphere.position.set(x, 0.85, y);
            this.markerGroup.add(sphere);

            // Label (using sprite)
            const label = this._createTextSprite(pkg.id, color);
            label.position.set(x, 1.2, y);
            this.markerGroup.add(label);
        });
    }

    _createTextSprite(text, color) {
        const canvas = document.createElement('canvas');
        canvas.width = 128;
        canvas.height = 64;
        const ctx = canvas.getContext('2d');
        ctx.font = 'bold 28px monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#' + new THREE.Color(color).getHexString();
        ctx.fillText(text, 64, 32);

        const texture = new THREE.CanvasTexture(canvas);
        const mat = new THREE.SpriteMaterial({ map: texture, transparent: true });
        const sprite = new THREE.Sprite(mat);
        sprite.scale.set(1.2, 0.6, 1);
        return sprite;
    }

    markDelivered(packageId, packages) {
        // Find the marker and change its color to green
        const idx = packages.findIndex(p => p.id === packageId);
        if (idx >= 0) {
            const [x, y] = packages[idx].destination;
            // Add a green check ring
            const ringGeo = new THREE.TorusGeometry(0.35, 0.05, 8, 32);
            const ringMat = new THREE.MeshStandardMaterial({
                color: 0x00ff88,
                emissive: 0x00ff88,
                emissiveIntensity: 0.5,
            });
            const ring = new THREE.Mesh(ringGeo, ringMat);
            ring.rotation.x = -Math.PI / 2;
            ring.position.set(x, 0.06, y);
            this.markerGroup.add(ring);
        }
    }

    getGridPosition(raycaster) {
        if (!this.clickableGround) return null;
        const intersects = raycaster.intersectObject(this.clickableGround);
        if (intersects.length > 0) {
            const p = intersects[0].point;
            const gx = Math.round(p.x);
            const gy = Math.round(p.z);
            if (gx >= 0 && gx < this.width && gy >= 0 && gy < this.height) {
                return [gx, gy];
            }
        }
        return null;
    }

    toggleObstacle(x, y) {
        const key = `${x},${y}`;
        if (key === '0,0') return; // Can't place obstacle on launch pad
        if (this.obstacles.has(key)) {
            this.obstacles.delete(key);
        } else {
            this.obstacles.add(key);
        }
        this._renderObstacles();
        document.getElementById('obstacle-count').textContent = this.obstacles.size;
    }

    getObstacleList() {
        return Array.from(this.obstacles).map(k => k.split(',').map(Number));
    }

    renderPaths(plannedDeliveries) {
        this.clearPaths();

        const colors = [0xc9a84c, 0x5dade2, 0x2ecc71, 0xe74c3c, 0x9b59b6, 0xe67e22];

        plannedDeliveries.forEach((delivery, i) => {
            const color = colors[i % colors.length];
            const outboundMat = new THREE.LineBasicMaterial({
                color,
                linewidth: 2,
                transparent: true,
                opacity: 0.7,
            });
            const returnMat = new THREE.LineBasicMaterial({
                color,
                linewidth: 2,
                transparent: true,
                opacity: 0.35,
            });

            // Outbound path (solid)
            if (delivery.outbound_path && delivery.outbound_path.length > 1) {
                const points = delivery.outbound_path.map(
                    ([x, y]) => new THREE.Vector3(x, 0.04, y)
                );
                const geo = new THREE.BufferGeometry().setFromPoints(points);
                const line = new THREE.Line(geo, outboundMat);
                this.pathGroup.add(line);

                // Small dots at each waypoint
                const dotGeo = new THREE.SphereGeometry(0.06, 8, 8);
                const dotMat = new THREE.MeshBasicMaterial({ color });
                for (let j = 1; j < points.length - 1; j++) {
                    const dot = new THREE.Mesh(dotGeo, dotMat);
                    dot.position.copy(points[j]);
                    this.pathGroup.add(dot);
                }
            }

            // Return path (dimmer)
            if (delivery.return_path && delivery.return_path.length > 1) {
                const points = delivery.return_path.map(
                    ([x, y]) => new THREE.Vector3(x, 0.03, y)
                );
                const geo = new THREE.BufferGeometry().setFromPoints(points);
                const line = new THREE.Line(geo, returnMat);
                this.pathGroup.add(line);
            }
        });
    }

    clearPaths() {
        while (this.pathGroup.children.length) {
            const child = this.pathGroup.children[0];
            if (child.geometry) child.geometry.dispose();
            if (child.material) child.material.dispose();
            this.pathGroup.remove(child);
        }
    }
}
