<script setup lang="ts">
// 递归可视化积木块节点

interface VisualBlock {
  type: 'op' | 'func' | 'leaf'
  label: string
  color: string
  path: number[]
  children: (VisualBlock | VisualSlot)[]
  nodeType: string
}

interface VisualSlot {
  type: 'slot'
  path: number[]
  child: VisualBlock | null
}

const props = defineProps<{
  node: VisualBlock
  activeSlot: number[]
}>()

const emit = defineEmits<{
  (e: 'select-slot', path: number[]): void
}>()

function isSlotActive(path: number[]): boolean {
  return props.activeSlot.join(',') === path.join(',')
}

function onSlotClick(path: number[]) {
  emit('select-slot', path)
}

function onSlotDragOver(e: DragEvent) {
  e.preventDefault()
  e.dataTransfer!.dropEffect = 'copy'
}

function onSlotDrop(e: DragEvent, path: number[]) {
  e.preventDefault()
  const blockId = e.dataTransfer!.getData('text/plain')
  if (blockId) {
    emit('select-slot', path)
  }
}
</script>

<template>
  <!-- 叶子节点（常量/字段） -->
  <div
    v-if="node.type === 'leaf'"
    class="v-block leaf"
    :style="{ backgroundColor: node.color + '22', borderColor: node.color }"
  >
    <span class="v-block-label" :style="{ color: node.color }">{{ node.label }}</span>
  </div>

  <!-- 运算符节点 -->
  <div v-else-if="node.type === 'op'" class="v-block op" :style="{ borderColor: node.color }">
    <div class="v-block-head" :style="{ backgroundColor: node.color }">
      <span class="v-op-symbol">{{ node.label }}</span>
    </div>
    <div class="v-op-body">
      <div class="v-op-arg">
        <!-- 左操作数 -->
        <template v-if="node.children[0]?.type === 'slot'">
          <div
            class="v-slot"
            :class="{ active: isSlotActive(node.children[0].path) }"
            :data-slot-path="node.children[0].path.join(',')"
            @click.stop="onSlotClick(node.children[0].path)"
            @dragover="onSlotDragOver"
            @drop="onSlotDrop($event, node.children[0].path)"
          >
            <span class="v-slot-text">拖入</span>
          </div>
        </template>
        <template v-else-if="node.children[0]">
          <VisualNode
            :node="node.children[0] as VisualBlock"
            :active-slot="activeSlot"
            @select-slot="(p: number[]) => emit('select-slot', p)"
          />
        </template>
      </div>
      <div class="v-op-symbol-inline" :style="{ color: node.color }">{{ node.label }}</div>
      <div class="v-op-arg">
        <!-- 右操作数 -->
        <template v-if="node.children[1]?.type === 'slot'">
          <div
            class="v-slot"
            :class="{ active: isSlotActive(node.children[1].path) }"
            :data-slot-path="node.children[1].path.join(',')"
            @click.stop="onSlotClick(node.children[1].path)"
            @dragover="onSlotDragOver"
            @drop="onSlotDrop($event, node.children[1].path)"
          >
            <span class="v-slot-text">拖入</span>
          </div>
        </template>
        <template v-else-if="node.children[1]">
          <VisualNode
            :node="node.children[1] as VisualBlock"
            :active-slot="activeSlot"
            @select-slot="(p: number[]) => emit('select-slot', p)"
          />
        </template>
      </div>
    </div>
  </div>

  <!-- 函数节点 -->
  <div v-else-if="node.type === 'func'" class="v-block func" :style="{ borderColor: node.color }">
    <div class="v-block-head" :style="{ backgroundColor: node.color }">
      <span class="v-func-name">{{ node.label }}()</span>
    </div>
    <div class="v-func-body">
      <span class="v-func-paren">(</span>
      <template v-for="(child, i) in node.children" :key="i">
        <span v-if="i > 0" class="v-func-comma">, </span>
        <template v-if="child.type === 'slot'">
          <div
            class="v-slot"
            :class="{ active: isSlotActive(child.path) }"
            :data-slot-path="child.path.join(',')"
            @click.stop="onSlotClick(child.path)"
            @dragover="onSlotDragOver"
            @drop="onSlotDrop($event, child.path)"
          >
            <span class="v-slot-text">拖入</span>
          </div>
        </template>
        <template v-else>
          <VisualNode
            :node="child as VisualBlock"
            :active-slot="activeSlot"
            @select-slot="(p: number[]) => emit('select-slot', p)"
          />
        </template>
      </template>
      <span class="v-func-paren">)</span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.v-block {
  display: inline-flex;
  align-items: center;
  border-radius: 8px;
  border: 2px solid;
  font-size: 13px;
  vertical-align: middle;
  transition: transform 0.1s, box-shadow 0.1s;
  cursor: default;

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  }

  &.leaf {
    padding: 4px 10px;
    font-weight: 600;
  }

  &.op,
  &.func {
    flex-direction: column;
    padding: 0;
    gap: 0;
  }
}

.v-block-head {
  padding: 3px 10px;
  border-radius: 6px 6px 0 0;
  font-weight: 700;
  font-size: 12px;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 4px;
  width: 100%;
  justify-content: center;
}

.v-op-symbol {
  font-size: 16px;
  font-weight: 800;
}

.v-func-name {
  font-size: 12px;
  letter-spacing: 0.5px;
}

.v-op-body {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 8px;
}

.v-op-arg {
  display: inline-flex;
  align-items: center;
}

.v-op-symbol-inline {
  font-size: 14px;
  font-weight: 800;
  padding: 0 2px;
}

.v-func-body {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 6px 8px;
  flex-wrap: wrap;
}

.v-func-paren {
  font-size: 16px;
  font-weight: 700;
  color: #666;
}

.v-func-comma {
  font-size: 14px;
  color: #666;
}

.v-child {
  display: inline-flex;
  align-items: center;
}

// 槽位样式
.v-slot {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 56px;
  height: 30px;
  border: 2px dashed #444;
  border-radius: 8px;
  padding: 2px 10px;
  cursor: pointer;
  transition: all 0.2s;
  background-color: rgba(255, 255, 255, 0.03);

  &:hover {
    border-color: #fb0079;
    background-color: rgba(251, 0, 121, 0.08);
  }

  &.active {
    border-color: #fb0079;
    background-color: rgba(251, 0, 121, 0.15);
    box-shadow: 0 0 0 3px rgba(251, 0, 121, 0.2);
  }

  .v-slot-text {
    font-size: 11px;
    color: #666;
    user-select: none;
  }
}
</style>
