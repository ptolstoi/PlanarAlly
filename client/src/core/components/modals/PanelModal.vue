<script lang="ts">
import Vue from "vue";
import Component from "vue-class-component";
import { Prop } from "vue-property-decorator";

import Modal from "@/core/components/modals/modal.vue";

@Component({
    components: {
        Modal,
    },
})
export default class PanelModal extends Vue {
    @Prop() panelName!: string;
    @Prop() categories!: string[];
    @Prop() visible!: boolean;

    selection = 0;

    mounted(): void {
        window.addEventListener("keyup", this.onKeyUp);
    }

    beforeDestroy(): void {
        window.removeEventListener("keyup", this.onKeyUp);
    }

    onKeyUp(event: KeyboardEvent): void {
        if (["INPUT", "TEXTAREA"].includes((event.target as HTMLElement).tagName)) return;

        if (event.ctrlKey || event.shiftKey || event.altKey || event.metaKey) return;

        if (event.key === "Escape") {
            this.hideModal();
        }
    }

    handleClick(event: { target: HTMLElement }): void {
        const child = event.target.firstElementChild;
        if (child instanceof HTMLInputElement) {
            child.click();
        }
    }

    hideModal(): void {
        this.$emit("update:visible", false);
    }
}
</script>

<template>
    <Modal :visible="visible" :colour="'rgba(255, 255, 255, 0.8)'" :mask="false">
        <div
            class="modal-header"
            slot="header"
            slot-scope="m"
            draggable="true"
            @dragstart="m.dragStart"
            @dragend="m.dragEnd"
        >
            <div><slot name="title"></slot></div>
            <div class="header-close" @click="hideModal" :title="$t('common.close')">
                <font-awesome-icon :icon="['far', 'window-close']" />
            </div>
        </div>
        <div class="modal-body" @click="handleClick">
            <div id="categories">
                <div
                    class="category"
                    :class="{ selected: selection === c }"
                    v-for="(category, c) in categories"
                    :key="category"
                    @click="selection = c"
                >
                    {{ category }}
                </div>
            </div>
            <slot :selection="selection"></slot>
        </div>
    </Modal>
</template>

<style scoped lang="scss">
.modal-header {
    background-color: #ff7052;
    padding: 10px;
    font-size: 20px;
    font-weight: bold;
    cursor: move;
}

.header-close {
    position: absolute;
    top: 5px;
    right: 5px;
}

.modal-body {
    display: flex;
    flex-direction: row;
}

* {
    box-sizing: border-box;
}

#categories {
    width: 7.5em;
    background-color: rgba(0, 0, 0, 0);
    border-right: solid 1px #82c8a0;
}

.category {
    border-bottom: solid 1px #82c8a0;
    padding: 5px;
    text-align: right;
    background-color: white;
    padding-right: 10px;
}

.selected,
.category:hover {
    background-color: #82c8a0;
    font-weight: bold;
    cursor: pointer;
    padding-right: 5px;
}

::v-deep {
    .panel {
        background-color: white;
        padding: 1em;
        display: grid;
        grid-template-columns: [setting] 1fr [value] 1fr [end];
        /* align-items: center; */
        align-content: start;
        min-height: 10em;

        button {
            padding: 6px 12px;
            border: 1px solid lightgray;
            border-radius: 0.25em;
            background-color: rgb(235, 235, 228);
        }

        input[type="number"],
        input[type="text"] {
            width: 100%;
        }
    }

    .row {
        display: contents;

        &:first-of-type > * {
            margin-top: 0.5em;
        }

        &:last-of-type > * {
            margin-bottom: 0.5em;
        }

        &:hover > * {
            cursor: pointer;
            text-shadow: 0px 0px 1px black;
        }
    }

    .row > *,
    .panel > *:not(.row) {
        display: flex;
        /* justify-content: center; */
        align-items: center;
        margin: 0.4em 0;
    }

    .smallrow > * {
        padding: 0.2em;
    }

    .header {
        line-height: 0.1em;
        margin: 20px 0 15px;
        font-style: italic;
        overflow: hidden;
        padding: 0.5em;

        &:after {
            position: relative;
            width: 100%;
            border-bottom: 1px solid #000;
            content: "";
            margin-right: -100%;
            margin-left: 10px;
            display: inline-block;
        }
    }

    .danger {
        color: #ff7052;

        &:hover {
            text-shadow: 0px 0px 1px #ff7052;
            cursor: pointer;
        }
    }

    .spanrow {
        grid-column: 1 / end;
        justify-self: normal;
        font-weight: bold;
    }

    input[type="checkbox"] {
        width: 16px;
        height: 23px;
        margin: 0;
        white-space: nowrap;
        display: inline-block;
    }

    .color-picker {
        margin: 0.5em 0 !important;
    }
}
</style>
