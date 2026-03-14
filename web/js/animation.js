export class AnimationController {
    constructor(drone, gridRenderer, onFrameUpdate) {
        this.drone = drone;
        this.gridRenderer = gridRenderer;
        this.onFrameUpdate = onFrameUpdate;

        this.moves = [];
        this.deliveries = [];
        this.recharges = [];
        this.plannedDeliveries = [];
        this.packages = [];
        this.batteryCapacity = 100;

        this.currentMoveIndex = -1;
        this.playing = false;
        this.speed = 0.3; // seconds per tick
        this.lastTickTime = 0;
        this.interpolationProgress = 0;

        // Path trail
        this.trailPoints = [];
    }

    load(result, packages, batteryCapacity) {
        this.moves = result.moves || [];
        this.deliveries = result.deliveries || [];
        this.recharges = result.recharges || [];
        this.plannedDeliveries = result.planned_deliveries || [];
        this.packages = packages;
        this.batteryCapacity = batteryCapacity;

        this.currentMoveIndex = -1;
        this.playing = false;
        this.interpolationProgress = 0;
        this.trailPoints = [];

        // Position drone at start
        this.drone.setPosition(0, 0.5, 0);
        this.drone.setVisible(true);
        this._updateHUD();
    }

    play() {
        this.playing = true;
        this.lastTickTime = performance.now();
    }

    pause() {
        this.playing = false;
    }

    togglePlayPause() {
        if (this.playing) {
            this.pause();
        } else {
            if (this.currentMoveIndex >= this.moves.length - 1) {
                this.reset();
            }
            this.play();
        }
        return this.playing;
    }

    reset() {
        this.currentMoveIndex = -1;
        this.playing = false;
        this.interpolationProgress = 0;
        this.trailPoints = [];
        this.drone.setPosition(0, 0.5, 0);
        this._updateHUD();
    }

    stepForward() {
        if (this.currentMoveIndex < this.moves.length - 1) {
            this.currentMoveIndex++;
            this.interpolationProgress = 1;
            this._applyMove(this.currentMoveIndex);
            this._checkEvents();
            this._updateHUD();
        }
    }

    stepBack() {
        if (this.currentMoveIndex > 0) {
            this.currentMoveIndex--;
            this.interpolationProgress = 1;
            this._applyMove(this.currentMoveIndex);
            this._updateHUD();
        } else if (this.currentMoveIndex === 0) {
            this.currentMoveIndex = -1;
            this.interpolationProgress = 0;
            this.drone.setPosition(0, 0.5, 0);
            this._updateHUD();
        }
    }

    setSpeed(speed) {
        this.speed = speed;
    }

    update(now) {
        if (!this.playing || this.moves.length === 0) {
            this.drone.update();
            return;
        }

        const elapsed = (now - this.lastTickTime) / 1000;
        this.interpolationProgress += elapsed / this.speed;

        if (this.interpolationProgress >= 1) {
            // Advance to next move
            this.interpolationProgress = 0;
            this.currentMoveIndex++;
            this.lastTickTime = now;

            if (this.currentMoveIndex >= this.moves.length) {
                this.currentMoveIndex = this.moves.length - 1;
                this.interpolationProgress = 1;
                this.playing = false;
                this._applyMove(this.currentMoveIndex);
                this._updateHUD();
                this.drone.update();
                return;
            }

            this._checkEvents();
        }

        // Interpolate position
        if (this.currentMoveIndex >= 0 && this.currentMoveIndex < this.moves.length) {
            const move = this.moves[this.currentMoveIndex];
            const t = Math.min(this.interpolationProgress, 1);

            const fromX = move.from[0];
            const fromZ = move.from[1];
            const toX = move.to[0];
            const toZ = move.to[1];

            const x = fromX + (toX - fromX) * t;
            const z = fromZ + (toZ - fromZ) * t;

            // Add slight hover bob
            const bob = Math.sin(now / 200) * 0.03;
            this.drone.setPosition(x, 0.5 + bob, z);
            this.drone.setRotation(move.direction);

            if (t >= 1) {
                this._updateHUD();
            }
        }

        this.lastTickTime = now;
        this.drone.update();
    }

    _applyMove(index) {
        const move = this.moves[index];
        const bob = Math.sin(performance.now() / 200) * 0.03;
        this.drone.setPosition(move.to[0], 0.5 + bob, move.to[1]);
        this.drone.setRotation(move.direction);
    }

    _checkEvents() {
        if (this.currentMoveIndex < 0) return;
        const currentTick = this.moves[this.currentMoveIndex].tick;

        // Check for delivery events
        for (const d of this.deliveries) {
            if (d.tick === currentTick) {
                this.gridRenderer.markDelivered(d.package_id, this.packages);
            }
        }
    }

    _updateHUD() {
        const frame = this._getCurrentFrame();
        if (this.onFrameUpdate) {
            this.onFrameUpdate(frame);
        }
    }

    _getCurrentFrame() {
        const totalTicks = this.moves.length > 0 ? this.moves[this.moves.length - 1].tick + 1 : 0;

        if (this.currentMoveIndex < 0) {
            return {
                tick: 0,
                totalTicks,
                battery: this.batteryCapacity,
                batteryCapacity: this.batteryCapacity,
                wind: '--',
                packageId: '--',
                packageWeight: 0,
                phase: 'IDLE',
                totalCost: 0,
            };
        }

        const move = this.moves[this.currentMoveIndex];
        const battery = move.battery_after;

        // Determine phase and current package
        let phase = 'IDLE';
        let packageId = '--';
        let packageWeight = 0;
        let totalCost = 0;

        // Calculate total cost up to current tick
        for (let i = 0; i <= this.currentMoveIndex; i++) {
            totalCost += this.moves[i].cost;
        }

        // Determine which delivery we're in
        for (const pd of this.plannedDeliveries) {
            if (move.tick >= pd.start_tick && move.tick < pd.end_tick) {
                packageId = pd.package_id;
                packageWeight = pd.weight_lbs;

                // Outbound or return?
                const outboundEndTick = pd.start_tick + pd.outbound_path.length - 1;
                if (move.tick < outboundEndTick) {
                    phase = 'OUTBOUND';
                } else {
                    phase = 'RETURN';
                }
                break;
            }
        }

        // Check if we just recharged
        for (const r of this.recharges) {
            if (move.tick === r.tick - 1) {
                phase = 'RECHARGING';
            }
        }

        return {
            tick: move.tick + 1,
            totalTicks,
            battery,
            batteryCapacity: this.batteryCapacity,
            wind: move.wind,
            packageId,
            packageWeight,
            phase,
            totalCost,
        };
    }

    get isPlaying() {
        return this.playing;
    }

    get isComplete() {
        return this.currentMoveIndex >= this.moves.length - 1;
    }
}
