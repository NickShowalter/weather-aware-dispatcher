import * as THREE from 'three';
import { SceneManager } from './scene.js';
import { GridRenderer } from './grid.js';
import { DroneModel } from './drone.js';
import { AnimationController } from './animation.js';
import { UIManager } from './ui.js';
import { runSimulation } from './api.js';

// Initialize
const canvas = document.getElementById('render-canvas');
const sceneManager = new SceneManager(canvas);
const gridRenderer = new GridRenderer(sceneManager.scene);
const drone = new DroneModel(sceneManager.scene);
const ui = new UIManager();

const animation = new AnimationController(drone, gridRenderer, (frame) => {
    ui.updateHUD(frame);
});

// Load default preset
const defaultPreset = ui.loadPreset('sample');
loadObstaclesFromPreset(defaultPreset);
rebuildGrid();

// --- Obstacle clicking with drag detection ---
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
let mouseDownPos = null;
const CLICK_THRESHOLD = 5; // pixels — if mouse moves more than this, it's a drag

canvas.addEventListener('mousedown', (e) => {
    mouseDownPos = { x: e.clientX, y: e.clientY };
});

canvas.addEventListener('mouseup', (e) => {
    if (!mouseDownPos) return;

    const dx = e.clientX - mouseDownPos.x;
    const dy = e.clientY - mouseDownPos.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    mouseDownPos = null;

    // Only toggle obstacle if it was a click, not a drag/orbit
    if (dist > CLICK_THRESHOLD) return;

    const rect = canvas.getBoundingClientRect();
    mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(mouse, sceneManager.camera);

    const pos = gridRenderer.getGridPosition(raycaster);
    if (pos) {
        gridRenderer.toggleObstacle(pos[0], pos[1]);
    }
});

// Animation loop
sceneManager.onAnimate(() => {
    animation.update(performance.now());
});

// --- Event Handlers ---

// Preset loading
document.getElementById('load-preset-btn').addEventListener('click', () => {
    const preset = document.getElementById('preset-select').value;
    const data = ui.loadPreset(preset);
    if (data) {
        loadObstaclesFromPreset(data);
        rebuildGrid();
        gridRenderer.clearPaths();
        animation.reset();
        document.getElementById('results-panel').classList.add('hidden');
    }
});

// Add package
document.getElementById('add-package-btn').addEventListener('click', () => {
    ui.addPackage();
});

// Add weather segment
document.getElementById('add-weather-btn').addEventListener('click', () => {
    ui.addWeatherSegment();
});

// Clear obstacles
document.getElementById('clear-obstacles-btn').addEventListener('click', () => {
    gridRenderer.obstacles.clear();
    gridRenderer._renderObstacles();
    document.getElementById('obstacle-count').textContent = '0';
});

// Grid dimension changes
document.getElementById('grid-width').addEventListener('change', rebuildGrid);
document.getElementById('grid-height').addEventListener('change', rebuildGrid);

// Run simulation
document.getElementById('run-btn').addEventListener('click', async () => {
    const btn = document.getElementById('run-btn');
    btn.disabled = true;
    ui.setStatus('Running simulation...', 'loading');

    try {
        const obstacles = gridRenderer.getObstacleList();
        const scenario = ui.collectScenario(obstacles);

        // Include algorithm config in the scenario
        const algoConfig = ui.getAlgorithmConfig();
        scenario.algorithm = algoConfig;

        const result = await runSimulation(scenario);

        if (!result.success && result.errors) {
            ui.setStatus('Validation errors: ' + result.errors.join('; '), 'error');
            btn.disabled = false;
            return;
        }

        if (result.error) {
            ui.setStatus('Simulation failed: ' + result.error, 'error');
        } else {
            const delivered = result.deliveries ? result.deliveries.length : 0;
            ui.setStatus(`Mission complete: ${delivered} packages delivered, ${result.total_battery_consumed.toFixed(2)} battery`, 'success');
        }

        // Rebuild grid with updated data
        rebuildGrid();

        // Render planned paths on the grid
        if (result.planned_deliveries) {
            gridRenderer.renderPaths(result.planned_deliveries);
        }

        // Load animation
        const batteryCapacity = scenario.config.battery_capacity;
        animation.load(result, ui.packages, batteryCapacity);

        // Show results panel — include warnings if any
        ui.showResults(result);

    } catch (err) {
        ui.setStatus('Error: ' + err.message, 'error');
    }

    btn.disabled = false;
});

// Playback controls
document.getElementById('btn-play-pause').addEventListener('click', () => {
    const playing = animation.togglePlayPause();
    document.getElementById('btn-play-pause').innerHTML = playing ? '&#x23F8;' : '&#x25B6;';
});

document.getElementById('btn-reset').addEventListener('click', () => {
    animation.reset();
    document.getElementById('btn-play-pause').innerHTML = '&#x25B6;';
});

document.getElementById('btn-step-forward').addEventListener('click', () => {
    animation.pause();
    animation.stepForward();
    document.getElementById('btn-play-pause').innerHTML = '&#x25B6;';
});

document.getElementById('btn-step-back').addEventListener('click', () => {
    animation.pause();
    animation.stepBack();
    document.getElementById('btn-play-pause').innerHTML = '&#x25B6;';
});

document.getElementById('playback-speed').addEventListener('input', (e) => {
    animation.setSpeed(parseFloat(e.target.value));
});

// Close results
document.getElementById('close-results').addEventListener('click', () => {
    document.getElementById('results-panel').classList.add('hidden');
});

// --- Helpers ---

function loadObstaclesFromPreset(preset) {
    if (!preset || !preset.obstacles) return;
    gridRenderer.obstacles.clear();
    for (const [x, y] of preset.obstacles) {
        gridRenderer.obstacles.add(`${x},${y}`);
    }
}

function rebuildGrid() {
    const w = parseInt(document.getElementById('grid-width').value);
    const h = parseInt(document.getElementById('grid-height').value);
    const obstacles = gridRenderer.getObstacleList();
    gridRenderer.build(w, h, obstacles, ui.packages);
    sceneManager.focusOn(0, 0, w, h);
    document.getElementById('obstacle-count').textContent = obstacles.length;
}
