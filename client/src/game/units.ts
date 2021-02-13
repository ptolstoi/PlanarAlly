import { GlobalPoint, LocalPoint, Ray } from "@/game/geom";
import { gameStore, DEFAULT_GRID_SIZE } from "@/game/store";

import { gameSettingsStore } from "./settings";

export function g2l(obj: GlobalPoint): LocalPoint {
    const z = gameStore.zoomFactor;
    const panX = gameStore.panX;
    const panY = gameStore.panY;
    return new LocalPoint((obj.x + panX) * z, (obj.y + panY) * z);
}

export function g2lx(x: number): number {
    return g2l(new GlobalPoint(x, 0)).x;
}

export function g2ly(y: number): number {
    return g2l(new GlobalPoint(0, y)).y;
}

export function g2lz(z: number): number {
    return z * gameStore.zoomFactor;
}

export function getUnitDistance(r: number): number {
    return (r / gameSettingsStore.unitSize) * DEFAULT_GRID_SIZE;
}

export function g2lr(r: number): number {
    return g2lz(getUnitDistance(r));
}

export function l2g(obj: LocalPoint): GlobalPoint;
// eslint-disable-next-line no-redeclare
export function l2g(obj: Ray<LocalPoint>): Ray<GlobalPoint>;
// eslint-disable-next-line no-redeclare
export function l2g(obj: LocalPoint | Ray<LocalPoint>): GlobalPoint | Ray<GlobalPoint> {
    const z = gameStore.zoomFactor;
    const panX = gameStore.panX;
    const panY = gameStore.panY;
    if (obj instanceof LocalPoint) {
        return new GlobalPoint(obj.x / z - panX, obj.y / z - panY);
    } else {
        return new Ray<GlobalPoint>(l2g(obj.origin), obj.direction.multiply(1 / z), obj.tMax);
    }
}

export function l2gx(x: number): number {
    return l2g(new LocalPoint(x, 0)).x;
}

export function l2gy(y: number): number {
    return l2g(new LocalPoint(0, y)).y;
}

export function l2gz(z: number): number {
    return z / gameStore.zoomFactor;
}

export function clampGridLine(point: number): number {
    return Math.round(point / DEFAULT_GRID_SIZE) * DEFAULT_GRID_SIZE;
}

export function clampToGrid(point: GlobalPoint): GlobalPoint {
    return new GlobalPoint(clampGridLine(point.x), clampGridLine(point.y));
}

export function toRadians(degrees: number): number {
    return (degrees * Math.PI) / 180;
}

// eslint-disable-next-line import/no-unused-modules
export function toDegrees(radians: number): number {
    return (radians * 180) / Math.PI;
}

(window as any).g2lx = g2lx;
(window as any).g2ly = g2ly;
