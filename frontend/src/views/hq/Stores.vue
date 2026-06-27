<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { hqAPI, type HQStore, type StoreCreateBody } from '@/api/hq'
import { ElMessage } from 'element-plus'

const loading = ref(true)
const stores = ref<HQStore[]>([])

// 新增门店弹窗
const showCreate = ref(false)
const creating = ref(false)
const form = ref<StoreCreateBody>({
  store_code: '',
  name: '',
  city: '',
  address: '',
})

async function loadStores() {
  loading.value = true
  try {
    const res = await hqAPI.getStores()
    stores.value = res.data.data
  } catch (e) {
    // 全局拦截器已提示
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  if (!form.value.store_code || !form.value.name) {
    ElMessage.warning('请填写门店编号和名称')
    return
  }
  creating.value = true
  try {
    const res = await hqAPI.createStore(form.value)
    ElMessage.success(res.data.message || '创建成功')
    showCreate.value = false
    form.value = { store_code: '', name: '', city: '', address: '' }
    await loadStores()
  } catch (e) {
    // 全局拦截器已提示
  } finally {
    creating.value = false
  }
}

function formatMoney(n: number) {
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return n.toLocaleString()
}

function statusText(s: string) {
  return s === 'active' ? '营业中' : '已停业'
}

onMounted(() => {
  loadStores()
})
</script>

<template>
  <div class="hq-stores">
    <div class="page-header">
      <h2>门店管理</h2>
      <button class="add-btn" @click="showCreate = true">+ 新增门店</button>
    </div>

    <!-- 门店列表 -->
    <div class="store-list" v-if="!loading">
      <div v-for="s in stores" :key="s.id" class="store-item">
        <div class="store-item-header">
          <span class="store-item-name">{{ s.name }}</span>
          <span class="store-item-status" :class="s.status">{{ statusText(s.status) }}</span>
        </div>
        <div class="store-item-meta">
          <span>{{ s.store_code }}</span>
          <span v-if="s.city"> · {{ s.city }}</span>
        </div>
        <div class="store-item-stats">
          <div class="stat">
            <span class="stat-val">¥{{ formatMoney(s.today_revenue) }}</span>
            <span class="stat-label">今日营收</span>
          </div>
          <div class="stat">
            <span class="stat-val">{{ s.employee_count }}</span>
            <span class="stat-label">员工</span>
          </div>
          <div class="stat">
            <span class="stat-val" :class="s.wework_status === 'active' ? 'ok' : 'pending'">
              {{ s.wework_status === 'active' ? '已接通' : '未接通' }}
            </span>
            <span class="stat-label">企微</span>
          </div>
        </div>
      </div>
      <div v-if="stores.length === 0" class="empty">
        暂无门店，点击右上角新增
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <!-- 新增门店弹窗 -->
    <Teleport to="body">
      <div v-if="showCreate" class="modal-overlay" @click.self="showCreate = false">
        <div class="modal">
          <h3>新增门店</h3>
          <div class="form-group">
            <label>门店编号 *</label>
            <input v-model="form.store_code" placeholder="如 WX-001" />
          </div>
          <div class="form-group">
            <label>门店名称 *</label>
            <input v-model="form.name" placeholder="如 无锡店" />
          </div>
          <div class="form-group">
            <label>城市</label>
            <input v-model="form.city" placeholder="如 无锡" />
          </div>
          <div class="form-group">
            <label>地址</label>
            <input v-model="form.address" placeholder="详细地址（选填）" />
          </div>
          <div class="form-group">
            <label>企微部门ID</label>
            <input v-model.number="form.wework_department_id" type="number" placeholder="企微通讯录部门ID（选填）" />
            <small>在企微后台「通讯录」中查看部门ID</small>
          </div>
          <div class="modal-actions">
            <button class="btn-cancel" @click="showCreate = false">取消</button>
            <button class="btn-confirm" :disabled="creating" @click="onCreate">
              {{ creating ? '创建中...' : '确认创建' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped lang="scss">
@use "@/styles/variables.scss" as *;

.hq-stores {
  padding: 16px;
  max-width: 600px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;

  h2 {
    font-size: 20px;
    font-weight: 700;
    color: $brand-white;
    margin: 0;
  }
}

.add-btn {
  padding: 8px 16px;
  background: $brand-primary;
  color: $brand-white;
  border: none;
  border-radius: $radius-sm;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;

  &:active { opacity: 0.8; }
}

.store-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.store-item {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: $radius-md;
  padding: 14px;
}

.store-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.store-item-name {
  font-size: 16px;
  font-weight: 600;
  color: $brand-white;
}

.store-item-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;

  &.active {
    background: rgba(76, 175, 80, 0.15);
    color: #4caf50;
  }
  &:not(.active) {
    background: rgba(244, 67, 54, 0.15);
    color: #f44336;
  }
}

.store-item-meta {
  font-size: 12px;
  color: $brand-text-light;
  margin-top: 2px;
}

.store-item-stats {
  display: flex;
  gap: 20px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}

.stat {
  display: flex;
  flex-direction: column;
}

.stat-val {
  font-size: 16px;
  font-weight: 700;
  color: $brand-white;
  font-family: $font-family-number;

  &.ok { color: #4caf50; font-size: 13px; }
  &.pending { color: #ff9800; font-size: 13px; }
}

.stat-label {
  font-size: 11px;
  color: $brand-text-light;
}

.empty, .loading {
  text-align: center;
  padding: 40px;
  color: $brand-text-light;
  font-size: 14px;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal {
  background: #1a1a1a;
  border-radius: $radius-lg;
  padding: 24px;
  width: 100%;
  max-width: 400px;

  h3 {
    color: $brand-white;
    font-size: 18px;
    margin: 0 0 16px;
  }
}

.form-group {
  margin-bottom: 14px;

  label {
    display: block;
    font-size: 13px;
    color: $brand-text-light;
    margin-bottom: 4px;
  }

  input {
    width: 100%;
    padding: 10px 12px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: $radius-sm;
    color: $brand-white;
    font-size: 14px;
    box-sizing: border-box;

    &:focus {
      outline: none;
      border-color: $brand-primary;
    }
  }

  small {
    display: block;
    font-size: 11px;
    color: $brand-text-light;
    margin-top: 4px;
  }
}

.modal-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.btn-cancel, .btn-confirm {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: $radius-sm;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-cancel {
  background: rgba(255, 255, 255, 0.08);
  color: $brand-white;
}

.btn-confirm {
  background: $brand-primary;
  color: $brand-white;

  &:disabled { opacity: 0.5; }
}
</style>
