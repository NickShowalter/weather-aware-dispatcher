const PRESETS = {
    sample: {
        grid_width: 20, grid_height: 20,
        manifest: [
            { id: 'pkg_1', destination: [18, 18], weight_lbs: 5 },
            { id: 'pkg_2', destination: [2, 15], weight_lbs: 10 },
            { id: 'pkg_3', destination: [15, 2], weight_lbs: 2 },
        ],
        weather_forecast: [
            { direction: 'EAST', start_tick: 0, end_tick: 49 },
            { direction: 'NORTH', start_tick: 50, end_tick: 99 },
            { direction: 'WEST', start_tick: 100, end_tick: null },
        ],
        obstacles: [[5, 5], [5, 6], [5, 7], [12, 15], [12, 16]],
        config: {},
    },
    stress_low_battery: {
        grid_width: 20, grid_height: 20,
        manifest: [
            { id: 'pkg_1', destination: [5, 5], weight_lbs: 3 },
            { id: 'pkg_2', destination: [2, 8], weight_lbs: 5 },
            { id: 'pkg_3', destination: [10, 3], weight_lbs: 8 },
        ],
        weather_forecast: [
            { direction: 'EAST', start_tick: 0, end_tick: null },
        ],
        obstacles: [[3, 3], [3, 4]],
        config: { battery_capacity: 40 },
    },
    stress_heavy_wind: {
        grid_width: 20, grid_height: 20,
        manifest: [
            { id: 'pkg_1', destination: [15, 10], weight_lbs: 5 },
            { id: 'pkg_2', destination: [3, 18], weight_lbs: 8 },
        ],
        weather_forecast: [
            { direction: 'WEST', start_tick: 0, end_tick: null },
        ],
        obstacles: [[7, 7], [7, 8], [7, 9]],
        config: { wind_against_multiplier: 4.0 },
    },
    edge_small_grid: {
        grid_width: 5, grid_height: 5,
        manifest: [
            { id: 'pkg_1', destination: [4, 4], weight_lbs: 3 },
            { id: 'pkg_2', destination: [1, 3], weight_lbs: 5 },
        ],
        weather_forecast: [
            { direction: 'NORTH', start_tick: 0, end_tick: null },
        ],
        obstacles: [[2, 2], [2, 3]],
        config: {},
    },
    edge_no_wind: {
        grid_width: 20, grid_height: 20,
        manifest: [
            { id: 'pkg_1', destination: [18, 18], weight_lbs: 5 },
            { id: 'pkg_2', destination: [2, 15], weight_lbs: 10 },
            { id: 'pkg_3', destination: [15, 2], weight_lbs: 2 },
        ],
        weather_forecast: [
            { direction: 'EAST', start_tick: 0, end_tick: null },
        ],
        obstacles: [[5, 5], [5, 6], [5, 7]],
        config: { wind_with_multiplier: 1.0, wind_against_multiplier: 1.0, wind_cross_multiplier: 1.0 },
    },
};

export class UIManager {
    constructor() {
        this.packages = [];
        this.weatherSegments = [];
        this._setupSliderSync();
    }

    _setupSliderSync() {
        const sliders = [
            ['battery-capacity', 'battery-capacity-val', 0],
            ['base-move-cost', 'base-move-cost-val', 1],
            ['wind-with', 'wind-with-val', 2],
            ['wind-against', 'wind-against-val', 1],
            ['wind-cross', 'wind-cross-val', 1],
            ['payload-rate', 'payload-rate-val', 2],
            ['payload-increment', 'payload-increment-val', 0],
            ['perm-threshold', 'perm-threshold-val', 0],
        ];

        for (const [sliderId, valId, decimals] of sliders) {
            const slider = document.getElementById(sliderId);
            const val = document.getElementById(valId);
            if (slider && val) {
                slider.addEventListener('input', () => {
                    val.textContent = parseFloat(slider.value).toFixed(decimals);
                });
            }
        }

        // Speed slider
        const speedSlider = document.getElementById('playback-speed');
        const speedVal = document.getElementById('speed-val');
        speedSlider.addEventListener('input', () => {
            speedVal.textContent = parseFloat(speedSlider.value).toFixed(2) + 's';
        });
    }

    loadPreset(name) {
        const preset = PRESETS[name];
        if (!preset) return;

        document.getElementById('grid-width').value = preset.grid_width;
        document.getElementById('grid-height').value = preset.grid_height;

        // Config
        const cfg = preset.config || {};
        this._setSlider('battery-capacity', cfg.battery_capacity || 100);
        this._setSlider('base-move-cost', cfg.base_move_cost || 1.0);
        this._setSlider('wind-with', cfg.wind_with_multiplier || 0.5);
        this._setSlider('wind-against', cfg.wind_against_multiplier || 2.0);
        this._setSlider('wind-cross', cfg.wind_cross_multiplier || 1.0);
        this._setSlider('payload-rate', cfg.payload_penalty_rate || 0.10);
        this._setSlider('payload-increment', cfg.payload_penalty_increment_lbs || 5);

        // Packages
        this.packages = preset.manifest.map(m => ({ ...m }));
        this._renderPackages();

        // Weather
        this.weatherSegments = preset.weather_forecast.map(w => ({ ...w }));
        this._renderWeather();

        return preset;
    }

    _setSlider(id, value) {
        const slider = document.getElementById(id);
        slider.value = value;
        slider.dispatchEvent(new Event('input'));
    }

    _renderPackages() {
        const container = document.getElementById('packages-list');
        container.innerHTML = '';

        this.packages.forEach((pkg, i) => {
            const div = document.createElement('div');
            div.className = 'package-entry';
            div.innerHTML = `
                <div class="pkg-header">
                    <input type="text" value="${pkg.id}" data-field="id" data-index="${i}">
                    <button class="btn-small" data-remove-pkg="${i}">Remove</button>
                </div>
                <div class="pkg-fields">
                    <div><label>X</label><input type="number" value="${pkg.destination[0]}" min="0" max="49" data-field="destX" data-index="${i}"></div>
                    <div><label>Y</label><input type="number" value="${pkg.destination[1]}" min="0" max="49" data-field="destY" data-index="${i}"></div>
                    <div><label>lbs</label><input type="number" value="${pkg.weight_lbs}" min="0" max="100" step="0.5" data-field="weight" data-index="${i}"></div>
                </div>
            `;
            container.appendChild(div);

            // Event listeners
            div.querySelector('[data-field="id"]').addEventListener('change', (e) => {
                this.packages[i].id = e.target.value;
            });
            div.querySelector('[data-field="destX"]').addEventListener('change', (e) => {
                this.packages[i].destination[0] = parseInt(e.target.value);
            });
            div.querySelector('[data-field="destY"]').addEventListener('change', (e) => {
                this.packages[i].destination[1] = parseInt(e.target.value);
            });
            div.querySelector('[data-field="weight"]').addEventListener('change', (e) => {
                this.packages[i].weight_lbs = parseFloat(e.target.value);
            });
            div.querySelector(`[data-remove-pkg="${i}"]`).addEventListener('click', () => {
                this.packages.splice(i, 1);
                this._renderPackages();
            });
        });
    }

    _renderWeather() {
        const container = document.getElementById('weather-list');
        container.innerHTML = '';

        this.weatherSegments.forEach((seg, i) => {
            const div = document.createElement('div');
            div.className = 'weather-entry';
            div.innerHTML = `
                <select data-weather-dir="${i}">
                    <option value="NORTH" ${seg.direction === 'NORTH' ? 'selected' : ''}>N</option>
                    <option value="SOUTH" ${seg.direction === 'SOUTH' ? 'selected' : ''}>S</option>
                    <option value="EAST" ${seg.direction === 'EAST' ? 'selected' : ''}>E</option>
                    <option value="WEST" ${seg.direction === 'WEST' ? 'selected' : ''}>W</option>
                </select>
                <div><label>Start</label><input type="number" value="${seg.start_tick}" min="0" data-weather-start="${i}"></div>
                <div><label>End</label><input type="number" value="${seg.end_tick ?? ''}" min="0" placeholder="null" data-weather-end="${i}"></div>
                <button class="btn-small" data-remove-weather="${i}">X</button>
            `;
            container.appendChild(div);

            div.querySelector(`[data-weather-dir="${i}"]`).addEventListener('change', (e) => {
                this.weatherSegments[i].direction = e.target.value;
            });
            div.querySelector(`[data-weather-start="${i}"]`).addEventListener('change', (e) => {
                this.weatherSegments[i].start_tick = parseInt(e.target.value);
            });
            div.querySelector(`[data-weather-end="${i}"]`).addEventListener('change', (e) => {
                const val = e.target.value.trim();
                this.weatherSegments[i].end_tick = val === '' ? null : parseInt(val);
            });
            div.querySelector(`[data-remove-weather="${i}"]`).addEventListener('click', () => {
                this.weatherSegments.splice(i, 1);
                this._renderWeather();
            });
        });
    }

    addPackage() {
        const nextId = `pkg_${this.packages.length + 1}`;
        this.packages.push({ id: nextId, destination: [5, 5], weight_lbs: 5 });
        this._renderPackages();
    }

    addWeatherSegment() {
        const lastEnd = this.weatherSegments.length > 0
            ? (this.weatherSegments[this.weatherSegments.length - 1].end_tick ?? 99)
            : -1;
        this.weatherSegments.push({
            direction: 'EAST',
            start_tick: lastEnd + 1,
            end_tick: null,
        });
        this._renderWeather();
    }

    collectScenario(obstacles) {
        return {
            grid_width: parseInt(document.getElementById('grid-width').value),
            grid_height: parseInt(document.getElementById('grid-height').value),
            manifest: this.packages,
            weather_forecast: this.weatherSegments,
            obstacles: obstacles,
            config: {
                battery_capacity: parseFloat(document.getElementById('battery-capacity').value),
                base_move_cost: parseFloat(document.getElementById('base-move-cost').value),
                wind_with_multiplier: parseFloat(document.getElementById('wind-with').value),
                wind_against_multiplier: parseFloat(document.getElementById('wind-against').value),
                wind_cross_multiplier: parseFloat(document.getElementById('wind-cross').value),
                payload_penalty_rate: parseFloat(document.getElementById('payload-rate').value),
                payload_penalty_increment_lbs: parseFloat(document.getElementById('payload-increment').value),
            },
        };
    }

    getAlgorithmConfig() {
        return {
            ordering: document.getElementById('algo-ordering').value,
            permThreshold: parseInt(document.getElementById('perm-threshold').value),
            pathfinding: document.getElementById('algo-pathfinding').value,
            crossCheck: document.getElementById('toggle-crosscheck').checked,
            strictBattery: document.getElementById('toggle-strict-battery').checked,
        };
    }

    setStatus(message, type) {
        const el = document.getElementById('status-message');
        el.textContent = message;
        el.className = `status-${type}`;
    }

    showResults(result) {
        const panel = document.getElementById('results-panel');
        const content = document.getElementById('results-content');

        const delivered = result.deliveries ? result.deliveries.length : 0;
        const total = delivered + (result.infeasible_packages ? result.infeasible_packages.length : 0);

        let html = `
            <div class="result-row"><span class="result-label">Packages Delivered</span><span class="result-value">${delivered}/${total}</span></div>
            <div class="result-row"><span class="result-label">Total Battery</span><span class="result-value">${result.total_battery_consumed.toFixed(2)}</span></div>
            <div class="result-row"><span class="result-label">Total Ticks</span><span class="result-value">${result.total_ticks}</span></div>
            <div class="result-row"><span class="result-label">Battery Swaps</span><span class="result-value">${result.recharges ? result.recharges.length : 0}</span></div>
        `;

        if (result.infeasible_packages && result.infeasible_packages.length > 0) {
            html += '<div style="margin-top:8px; color:#ff4444;">';
            for (const inf of result.infeasible_packages) {
                html += `<div>${inf.package_id}: ${inf.reason}</div>`;
            }
            html += '</div>';
        }

        content.innerHTML = html;
        panel.classList.remove('hidden');
    }

    updateHUD(frame) {
        document.getElementById('hud-tick').textContent = `${frame.tick} / ${frame.totalTicks}`;
        document.getElementById('hud-package').textContent =
            frame.packageId === '--' ? '--' : `${frame.packageId} (${frame.packageWeight} lbs)`;
        const phaseEl = document.getElementById('hud-phase');
        phaseEl.textContent = frame.phase;
        phaseEl.className = 'hud-value hud-phase-' + frame.phase.toLowerCase();
        document.getElementById('hud-total-cost').textContent = frame.totalCost.toFixed(2);

        // Wind
        const windArrows = { NORTH: '\u2191', SOUTH: '\u2193', EAST: '\u2192', WEST: '\u2190' };
        const windText = frame.wind === '--' ? '--' : `${windArrows[frame.wind] || ''} ${frame.wind}`;
        document.getElementById('hud-wind').textContent = windText;

        // Battery bar
        const pct = Math.max(0, (frame.battery / frame.batteryCapacity) * 100);
        const fill = document.getElementById('battery-bar-fill');
        fill.style.width = pct + '%';
        fill.className = '';
        if (pct < 30) fill.classList.add('critical');
        else if (pct < 60) fill.classList.add('warning');
        document.getElementById('battery-percentage').textContent = pct.toFixed(1) + '%';
    }
}
