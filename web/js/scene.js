import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export class SceneManager {
    constructor(canvas) {
        this.canvas = canvas;
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x0a0a14);

        // Renderer
        this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
        this.renderer.toneMappingExposure = 1.2;
        this._updateSize();

        // Camera
        this.camera = new THREE.PerspectiveCamera(50, this.canvas.clientWidth / this.canvas.clientHeight, 0.1, 200);
        this.camera.position.set(10, 18, 22);
        this.camera.lookAt(10, 0, 10);

        // Controls
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.target.set(10, 0, 10);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.08;
        this.controls.maxPolarAngle = Math.PI / 2.1;
        this.controls.minDistance = 5;
        this.controls.maxDistance = 60;
        this.controls.update();

        // Lighting
        const ambient = new THREE.AmbientLight(0x404060, 0.6);
        this.scene.add(ambient);

        const directional = new THREE.DirectionalLight(0xffffff, 1.0);
        directional.position.set(15, 20, 10);
        directional.castShadow = true;
        directional.shadow.mapSize.width = 2048;
        directional.shadow.mapSize.height = 2048;
        directional.shadow.camera.near = 0.5;
        directional.shadow.camera.far = 60;
        directional.shadow.camera.left = -25;
        directional.shadow.camera.right = 25;
        directional.shadow.camera.top = 25;
        directional.shadow.camera.bottom = -25;
        this.scene.add(directional);

        const fill = new THREE.DirectionalLight(0x4488ff, 0.3);
        fill.position.set(-10, 10, -10);
        this.scene.add(fill);

        // Resize handler
        window.addEventListener('resize', () => this._updateSize());

        // Animation loop
        this._animateCallbacks = [];
        this._animate();
    }

    _updateSize() {
        const w = this.canvas.clientWidth;
        const h = this.canvas.clientHeight;
        this.renderer.setSize(w, h, false);
        if (this.camera) {
            this.camera.aspect = w / h;
            this.camera.updateProjectionMatrix();
        }
    }

    _animate() {
        requestAnimationFrame(() => this._animate());
        this.controls.update();
        for (const cb of this._animateCallbacks) cb();
        this.renderer.render(this.scene, this.camera);
    }

    onAnimate(callback) {
        this._animateCallbacks.push(callback);
    }

    focusOn(x, z, gridWidth, gridHeight) {
        const cx = gridWidth / 2;
        const cz = gridHeight / 2;
        const dist = Math.max(gridWidth, gridHeight) * 1.1;
        this.camera.position.set(cx, dist * 0.8, cz + dist * 0.6);
        this.controls.target.set(cx, 0, cz);
        this.controls.update();
    }
}
