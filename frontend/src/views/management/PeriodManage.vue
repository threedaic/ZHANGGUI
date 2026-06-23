<script setup lang="ts">
// 账期管理页面（锁定/关账/重新开放）
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getPeriod,
  lockPeriod,
  closePeriod,
  reopenPeriod,
  type PeriodInfo,
  type PeriodStatus,
} from '@/api/period'
import dayjs from 'dayjs'

const period = ref<string>(dayjs().format('YYYY-MM'))
const info = ref<PeriodInfo | null>(null)
const loading = ref(false)
const acting = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await getPeriod(period.value)
    info.value = res.data.data
  } catch (e) {
    info.value = null
  } finally {
    loading.value = false
  }
}

async function doAction(action: 'lock' | 'close' | 'reopen') {
  if (!info.value) return
  const actionMap: Record<string, { label: string; fn: (p: string) => Promise<unknown> }> = {
    lock: { label: '锁定', fn: lockPeriod },
    close: { label: '关账', fn: closePeriod },
    reopen: { label: '重新开放', fn: reopenPeriod },
  }
  const conf = actionMap[action]
  try {
    await ElMessageBox.confirm(
      `确认对账期 ${period.value} 执行「${conf.label}」操作？`,
      `${conf.label}账期`,
      { type: 'warning' }
    )
    acting.value = true
    await conf.fn(period.value)
    ElMessage.success(`${conf.label}成功`)
    await load()
  } catch (e) {
    /* 取消或错误 */
  } finally {
    acting.value = false
  }
}

const statusMeta: Record<PeriodStatus, { label: string; desc: string; color: string }> = {
  open: {
    label: '开放中',
    desc: '可生成、修改、确认工资',
    color: 'rgba(251, 0, 121, 0.15)',
  },
  locked: {
    label: '已锁定',
    desc: '不可修改，但可查看；可关账或重新开放',
    color: '#555',
  },
  closed: {
    label: '已关账',
    desc: '终态，仅可查看；如需修改须先重新开放',
    color: '#333',
  },
}

watch(period, load)
onMounted(load)
</script>

<template>
  <div class="period-page">
    <div class="top-bar">
      <input v-model="period" type="month" class="month-input" />
    </div>

    <div v-loading="loading" class="content">
      <div v-if="!info && !loading" class="empty-state">
        暂无该账期信息
      </div>

      <div v-if="info" class="card status-card">
        <div class="status-badge" :style="{ backgroundColor: statusMeta[info.status].color }">
          {{ statusMeta[info.status].label }}
        </div>
        <div class="period-label">账期 {{ info.period }}</div>
        <div class="status-desc">{{ statusMeta[info.status].desc }}</div>
        <div v-if="info.message" class="status-msg">{{ info.message }}</div>
      </div>

      <div v-if="info" class="card">
        <div class="section-title">操作日志</div>
        <div class="log-row">
          <span>锁定时间</span>
          <span>{{ info.locked_at || '-' }}</span>
        </div>
        <div class="log-row">
          <span>关账时间</span>
          <span>{{ info.closed_at || '-' }}</span>
        </div>
        <div v-if="info.note" class="log-row">
          <span>备注</span>
          <span>{{ info.note }}</span>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div v-if="info" class="actions">
        <button
          v-if="info.status === 'open'"
          class="btn-primary"
          :disabled="acting"
          @click="doAction('lock')"
        >
          锁定账期
        </button>
        <button
          v-if="info.status === 'locked'"
          class="btn-primary"
          :disabled="acting"
          @click="doAction('close')"
        >
          关账
        </button>
        <button
          v-if="info.status !== 'open'"
          class="btn-ghost"
          :disabled="acting"
          @click="doAction('reopen')"
        >
          重新开放
        </button>
      </div>

      <!-- 流程说明 -->
      <div class="card flow-card">
        <div class="section-title">账期流程</div>
        <div class="flow">
          <div class="flow-step">
            <div class="step-dot open"></div>
            <div class="step-label">开放</div>
            <div class="step-desc">可编辑</div>
          </div>
          <div class="flow-arrow">→</div>
          <div class="flow-step">
            <div class="step-dot locked"></div>
            <div class="step-label">锁定</div>
            <div class="step-desc">只读</div>
          </div>
          <div class="flow-arrow">→</div>
          <div class="flow-step">
            <div class="step-dot closed"></div>
            <div class="step-label">关账</div>
            <div class="step-desc">终态</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.period-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.top-bar {
  display: flex;
}

.month-input {
  flex: 1;
  height: 38px;
  background-color: $color-bg;
  border: 1px solid $color-divider;
  border-radius: $radius-sm;
  padding: 0 10px;
  color: $brand-white;
  font-size: 14px;
  outline: none;
}

.card {
  background-color: $color-bg;
  border-radius: $radius-md;
  padding: 16px;
}

.status-card {
  text-align: center;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  color: $brand-white;
  margin-bottom: 8px;
}

.period-label {
  font-size: 20px;
  color: $brand-white;
  font-weight: 600;
  margin-bottom: 4px;
}

.status-desc {
  font-size: 12px;
  color: #888;
}

.status-msg {
  margin-top: 8px;
  padding: 8px;
  background-color: $color-black;
  border-radius: $radius-sm;
  font-size: 12px;
  color: $brand-primary;
}

.section-title {
  font-size: 13px;
  color: $brand-primary;
  margin-bottom: 12px;
  font-weight: 600;
}

.log-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;

  span:first-child {
    color: #888;
  }

  span:last-child {
    color: $brand-white;
  }
}

.actions {
  display: flex;
  gap: 12px;

  button {
    flex: 1;
    height: 44px;
  }
}

.flow-card {
  text-align: center;
}

.flow {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 0;
}

.flow-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.step-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;

  &.open {
    background-color: $brand-primary;
  }
  &.locked {
    background-color: #555;
  }
  &.closed {
    background-color: #333;
    border: 1px solid #555;
  }
}

.step-label {
  font-size: 12px;
  color: $brand-white;
  font-weight: 600;
}

.step-desc {
  font-size: 10px;
  color: #888;
}

.flow-arrow {
  color: #555;
  font-size: 16px;
}
</style>
