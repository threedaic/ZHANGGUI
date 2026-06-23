<template>
  <div class="signature-pad-wrapper">
    <div class="signature-label">手写签名</div>
    <div class="signature-canvas-container" ref="containerRef">
      <canvas
        ref="canvasRef"
        class="signature-canvas"
        @mousedown="onStart"
        @mousemove="onMove"
        @mouseup="onEnd"
        @mouseleave="onEnd"
        @touchstart.prevent="onTouchStart"
        @touchmove.prevent="onTouchMove"
        @touchend="onEnd"
      ></canvas>
      <div v-if="!hasContent" class="signature-placeholder">在此处签名</div>
    </div>
    <div class="signature-actions">
      <button class="btn-clear" @click="clear">清除</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'

const canvasRef = ref<HTMLCanvasElement | null>(null)
const containerRef = ref<HTMLDivElement | null>(null)
const hasContent = ref(false)

let ctx: CanvasRenderingContext2D | null = null
let drawing = false

function initCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return
  canvas.width = canvas.offsetWidth * 2
  canvas.height = (canvas.offsetHeight || 120) * 2
  ctx = canvas.getContext('2d')
  if (ctx) {
    ctx.scale(2, 2)
    ctx.strokeStyle = '#FFFFFF'
    ctx.lineWidth = 2.5
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
  }
}

function onStart(e: MouseEvent) {
  drawing = true
  ctx?.beginPath()
  const rect = canvasRef.value!.getBoundingClientRect()
  ctx?.moveTo(e.clientX - rect.left, e.clientY - rect.top)
}

function onMove(e: MouseEvent) {
  if (!drawing || !ctx) return
  const rect = canvasRef.value!.getBoundingClientRect()
  ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top)
  ctx.stroke()
  hasContent.value = true
}

function onEnd() {
  drawing = false
  ctx?.closePath()
}

// Touch events
function getTouchPos(e: TouchEvent) {
  const rect = canvasRef.value!.getBoundingClientRect()
  const touch = e.touches[0]
  return { x: touch.clientX - rect.left, y: touch.clientY - rect.top }
}

function onTouchStart(e: TouchEvent) {
  drawing = true
  const pos = getTouchPos(e)
  ctx?.beginPath()
  ctx?.moveTo(pos.x, pos.y)
}

function onTouchMove(e: TouchEvent) {
  if (!drawing || !ctx) return
  const pos = getTouchPos(e)
  ctx.lineTo(pos.x, pos.y)
  ctx.stroke()
  hasContent.value = true
}

function clear() {
  const canvas = canvasRef.value
  if (canvas && ctx) {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    hasContent.value = false
  }
}

function getDataURL(): string {
  return canvasRef.value?.toDataURL('image/png') || ''
}

function isEmpty(): boolean {
  return !hasContent.value
}

defineExpose({ getDataURL, isEmpty, clear })

const resizeObserver = new ResizeObserver(() => {
  nextTick(initCanvas)
})

onMounted(() => {
  nextTick(initCanvas)
  if (containerRef.value) {
    resizeObserver.observe(containerRef.value)
  }
})

onUnmounted(() => {
  resizeObserver.disconnect()
})
</script>

<style scoped>
.signature-pad-wrapper {
  padding: 0 16px;
  margin-bottom: 16px;
}

.signature-label {
  font-size: 13px;
  font-weight: 600;
  color: #C8C8C8;
  margin-bottom: 8px;
}

.signature-canvas-container {
  position: relative;
  width: 100%;
  height: 140px;
  background: #1a1a1a;
  border: 1.5px solid #333333;
  border-radius: 8px;
  overflow: hidden;
}

.signature-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  touch-action: none;
}

.signature-placeholder {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 14px;
  color: #7A7C80;
  pointer-events: none;
}

.signature-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}

.btn-clear {
  background: transparent;
  border: 1px solid #333333;
  border-radius: 6px;
  padding: 4px 16px;
  font-size: 12px;
  color: #7A7C80;
  cursor: pointer;
}
</style>
