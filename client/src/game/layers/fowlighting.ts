import { InvalidationMode, SyncMode } from "@/core/models/types";
import { layerManager } from "@/game/layers/manager";
import { Shape } from "@/game/shapes/shape";
import { Circle } from "@/game/shapes/variants/circle";
import { g2l, g2lr, g2lx, g2ly, g2lz, getUnitDistance, toRadians } from "@/game/units";
import { getFogColour } from "@/game/utils";
import { getVisionSources } from "@/game/visibility/utils";

import { gameSettingsStore } from "../settings";
import { gameStore } from "../store";
import { TriangulationTarget } from "../visibility/te/pa";
import { computeVisibility } from "../visibility/te/te";

import { FowLayer } from "./fow";
import { floorStore } from "./store";

export class FowLightingLayer extends FowLayer {
    addShape(shape: Shape, sync: SyncMode, invalidate: InvalidationMode, snappable = true): void {
        super.addShape(shape, sync, invalidate, snappable);
        if (shape.options.has("preFogShape") && shape.options.get("preFogShape")) {
            this.preFogShapes.push(shape);
        }
    }

    removeShape(shape: Shape, sync: SyncMode, recalculate: boolean): boolean {
        let idx = -1;
        if (shape.options.has("preFogShape") && shape.options.get("preFogShape")) {
            idx = this.preFogShapes.findIndex((s) => s.uuid === shape.uuid);
        }
        const remove = super.removeShape(shape, sync, recalculate);
        if (remove && idx >= 0) this.preFogShapes.splice(idx, 1);
        return remove;
    }

    draw(): void {
        if (!this.valid) {
            const originalOperation = this.ctx.globalCompositeOperation;
            super._draw();

            // At all times provide a minimal vision range to prevent losing your tokens in fog.
            if (
                gameSettingsStore.fullFow &&
                layerManager.hasLayer(floorStore.currentFloor, "tokens") &&
                floorStore.currentFloor.id === this.floor
            ) {
                for (const sh of gameStore.activeTokens) {
                    const shape = layerManager.UUIDMap.get(sh)!;
                    if ((shape.options.get("skipDraw") ?? false) === true) continue;
                    if (shape.floor.id !== floorStore.currentFloor.id) continue;
                    const bb = shape.getBoundingBox();
                    const lcenter = g2l(shape.center());
                    const alm = 0.8 * g2lz(bb.w);
                    this.ctx.beginPath();
                    this.ctx.arc(lcenter.x, lcenter.y, alm, 0, 2 * Math.PI);
                    const gradient = this.ctx.createRadialGradient(
                        lcenter.x,
                        lcenter.y,
                        alm / 2,
                        lcenter.x,
                        lcenter.y,
                        alm,
                    );
                    gradient.addColorStop(0, "rgba(0, 0, 0, 1)");
                    gradient.addColorStop(1, "rgba(0, 0, 0, 0)");
                    this.ctx.fillStyle = gradient;
                    this.ctx.fill();
                }
            }

            // First cut out all the light sources
            for (const light of getVisionSources(this.floor)) {
                const shape = layerManager.UUIDMap.get(light.shape);
                if (shape === undefined) continue;
                const aura = shape.getAuras(true).find((a) => a.uuid === light.aura);
                if (aura === undefined) continue;

                if (!shape.ownedBy(true, { visionAccess: true }) && !aura.visible) continue;

                const auraValue = aura.value > 0 && !isNaN(aura.value) ? aura.value : 0;
                const auraDim = aura.dim > 0 && !isNaN(aura.dim) ? aura.dim : 0;

                const auraLength = getUnitDistance(auraValue + auraDim);
                const center = shape.center();
                const lcenter = g2l(center);
                const innerRange = g2lr(auraValue + auraDim);

                const auraCircle = new Circle(center, auraLength);
                if (!auraCircle.visibleInCanvas(this.ctx.canvas, { includeAuras: true })) continue;

                this.vCtx.globalCompositeOperation = "source-over";
                this.vCtx.fillStyle = "rgba(0, 0, 0, 1)";
                const polygon = computeVisibility(center, TriangulationTarget.VISION, shape.floor.id);
                this.vCtx.beginPath();

                if (polygon.length > 0) {
                    this.vCtx.moveTo(g2lx(polygon[0][0]), g2ly(polygon[0][1]));
                    for (const point of polygon) this.vCtx.lineTo(g2lx(point[0]), g2ly(point[1]));
                }
                this.vCtx.closePath();
                this.vCtx.fill();
                if (auraDim > 0) {
                    // Fill the light aura with a radial dropoff towards the outside.
                    const gradient = this.vCtx.createRadialGradient(
                        lcenter.x,
                        lcenter.y,
                        g2lr(auraValue),
                        lcenter.x,
                        lcenter.y,
                        innerRange,
                    );
                    gradient.addColorStop(0, "rgba(0, 0, 0, 1)");
                    gradient.addColorStop(1, "rgba(0, 0, 0, 0)");
                    this.vCtx.fillStyle = gradient;
                } else {
                    this.vCtx.fillStyle = "rgba(0, 0, 0, 1)";
                }
                this.vCtx.globalCompositeOperation = "source-in";
                this.vCtx.beginPath();

                const angleA = toRadians(aura.direction - aura.angle / 2);
                const angleB = toRadians(aura.direction + aura.angle / 2);

                if (aura.angle < 360) {
                    this.vCtx.moveTo(lcenter.x, lcenter.y);
                    this.vCtx.lineTo(
                        lcenter.x + innerRange * Math.cos(angleA),
                        lcenter.y + innerRange * Math.sin(angleA),
                    );
                }
                this.vCtx.arc(lcenter.x, lcenter.y, innerRange, angleA, angleB);
                if (aura.angle < 360) {
                    this.vCtx.lineTo(lcenter.x, lcenter.y);
                }

                this.vCtx.fill();
                this.ctx.drawImage(this.virtualCanvas, 0, 0);
            }

            const activeFloor = floorStore.currentFloor.id;
            if (gameSettingsStore.fowLos && this.floor === activeFloor) {
                this.ctx.globalCompositeOperation = "source-in";
                this.ctx.drawImage(layerManager.getLayer(floorStore.currentFloor, "fow-players")!.canvas, 0, 0);
            }

            for (const preShape of this.preFogShapes) {
                if (!preShape.visibleInCanvas(this.canvas, { includeAuras: true })) continue;
                const ogComposite = preShape.globalCompositeOperation;
                if (!gameSettingsStore.fullFow) {
                    if (preShape.globalCompositeOperation === "source-over")
                        preShape.globalCompositeOperation = "destination-out";
                    else if (preShape.globalCompositeOperation === "destination-out")
                        preShape.globalCompositeOperation = "source-over";
                }
                preShape.draw(this.ctx);
                preShape.globalCompositeOperation = ogComposite;
            }

            if (gameSettingsStore.fullFow && this.floor === activeFloor) {
                this.ctx.globalCompositeOperation = "source-out";
                this.ctx.fillStyle = getFogColour();
                this.ctx.fillRect(0, 0, this.ctx.canvas.width, this.ctx.canvas.height);
            }

            super.draw(false);

            this.ctx.globalCompositeOperation = originalOperation;
        }
    }
}
