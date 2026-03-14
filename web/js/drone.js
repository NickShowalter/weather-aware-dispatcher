import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export class DroneModel {
    constructor(scene) {
        this.scene = scene;
        this.group = new THREE.Group();
        this.group.visible = false;
        this.scene.add(this.group);

        this.mixer = null;
        this.rotors = [];
        this.modelLoaded = false;
        this.clock = new THREE.Clock();

        this._loadModel();
    }

    _loadModel() {
        const loader = new GLTFLoader();
        loader.load(
            'models/quadcopter_drone/scene.gltf',
            (gltf) => {
                const model = gltf.scene;

                // Calculate bounding box for scaling
                const box = new THREE.Box3().setFromObject(model);
                const size = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 0.6 / maxDim; // fit in ~0.6 units
                model.scale.set(scale, scale, scale);

                // Center the model
                const center = box.getCenter(new THREE.Vector3());
                model.position.set(
                    -center.x * scale,
                    -center.y * scale,
                    -center.z * scale
                );

                model.traverse((child) => {
                    if (child.isMesh) {
                        child.castShadow = true;
                        child.receiveShadow = true;
                    }
                });

                this.group.add(model);
                this.modelLoaded = true;

                // Set up animation mixer if model has animations
                if (gltf.animations && gltf.animations.length > 0) {
                    this.mixer = new THREE.AnimationMixer(model);
                    gltf.animations.forEach(clip => {
                        this.mixer.clipAction(clip).play();
                    });
                }
            },
            undefined,
            (err) => {
                console.warn('Failed to load drone GLTF, using fallback geometry:', err);
                this._createFallback();
            }
        );
    }

    _createFallback() {
        // Simple drone: body + 4 rotors
        const bodyGeo = new THREE.CylinderGeometry(0.15, 0.2, 0.1, 8);
        const bodyMat = new THREE.MeshStandardMaterial({ color: 0x444444, metalness: 0.6, roughness: 0.4 });
        const body = new THREE.Mesh(bodyGeo, bodyMat);
        body.castShadow = true;
        this.group.add(body);

        // Arms + rotors
        const armPositions = [
            [0.25, 0, 0.25],
            [-0.25, 0, 0.25],
            [0.25, 0, -0.25],
            [-0.25, 0, -0.25],
        ];

        const armMat = new THREE.MeshStandardMaterial({ color: 0x333333, metalness: 0.5 });
        const rotorMat = new THREE.MeshStandardMaterial({
            color: 0x888888,
            transparent: true,
            opacity: 0.7,
        });

        for (const pos of armPositions) {
            // Arm
            const armGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.35, 4);
            const arm = new THREE.Mesh(armGeo, armMat);
            arm.rotation.z = Math.PI / 2;
            arm.rotation.y = Math.atan2(pos[2], pos[0]);
            arm.position.set(pos[0] / 2, 0.02, pos[2] / 2);
            this.group.add(arm);

            // Rotor disc
            const rotorGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.01, 16);
            const rotor = new THREE.Mesh(rotorGeo, rotorMat);
            rotor.position.set(pos[0], 0.06, pos[2]);
            this.group.add(rotor);
            this.rotors.push(rotor);
        }

        this.modelLoaded = true;
    }

    update() {
        if (this.mixer) {
            const delta = this.clock.getDelta();
            this.mixer.update(delta);
        }
        // Spin fallback rotors
        for (const rotor of this.rotors) {
            rotor.rotation.y += 0.4;
        }
    }

    setPosition(x, y, z) {
        this.group.position.set(x, y, z);
    }

    setVisible(visible) {
        this.group.visible = visible;
    }

    setRotation(direction) {
        // Rotate drone to face movement direction
        const angles = {
            'NORTH': Math.PI,      // face +z (north in grid = +z in 3D)
            'SOUTH': 0,
            'EAST': Math.PI / 2,
            'WEST': -Math.PI / 2,
        };
        if (direction in angles) {
            this.group.rotation.y = angles[direction];
        }
    }
}
