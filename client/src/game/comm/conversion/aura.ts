import { ServerAura } from "@/game/comm/types/shapes";

import { Aura } from "../../shapes/interfaces";

export const aurasFromServer = (...auras: ServerAura[]): Aura[] => {
    const result = [];
    for (const aura of auras) {
        result.push({
            uuid: aura.uuid,
            active: aura.active,
            visionSource: aura.vision_source,
            visible: aura.visible,
            name: aura.name,
            value: aura.value,
            dim: aura.dim,
            colour: aura.colour,
            borderColour: aura.border_colour,
            angle: aura.angle,
            direction: aura.direction,
            temporary: false,
        });
    }
    return result;
};

export const aurasToServer = (shape: string, auras: Aura[]): ServerAura[] => {
    const result = [];
    for (const aura of auras) {
        result.push({
            uuid: aura.uuid,
            active: aura.active,
            vision_source: aura.visionSource,
            visible: aura.visible,
            name: aura.name,
            value: aura.value,
            dim: aura.dim,
            colour: aura.colour,
            border_colour: aura.borderColour,
            angle: aura.angle,
            direction: aura.direction,
            shape,
        });
    }
    return result;
};

export const partialAuraToServer = (aura: Partial<Aura>): Partial<ServerAura> => {
    return {
        uuid: aura.uuid,
        active: aura.active,
        vision_source: aura.visionSource,
        visible: aura.visible,
        name: aura.name,
        value: aura.value,
        dim: aura.dim,
        colour: aura.colour,
        border_colour: aura.borderColour,
        angle: aura.angle,
        direction: aura.direction,
    };
};

export const partialAuraFromServer = (aura: Partial<ServerAura>): Partial<Aura> => {
    const partial: Partial<Aura> = {};
    if ("uuid" in aura) partial.uuid = aura.uuid;
    if ("active" in aura) partial.active = aura.active;
    if ("vision_source" in aura) partial.visionSource = aura.vision_source;
    if ("visible" in aura) partial.visible = aura.visible;
    if ("name" in aura) partial.name = aura.name;
    if ("value" in aura) partial.value = aura.value;
    if ("dim" in aura) partial.dim = aura.dim;
    if ("colour" in aura) partial.colour = aura.colour;
    if ("border_colour" in aura) partial.borderColour = aura.border_colour;
    if ("angle" in aura) partial.angle = aura.angle;
    if ("direction" in aura) partial.direction = aura.direction;
    return partial;
};
