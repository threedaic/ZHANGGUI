<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import BottomNav from '@/components/BottomNav.vue'
import { useAuthStore } from '@/stores/auth'
import { storeAPI, type StoreBrief } from '@/api/store'
import { switchStore } from '@/api/auth'
import { ElMessage, ElMessageBox } from 'element-plus'

defineProps<{
  title?: string
  showBack?: boolean
}>()

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const stores = ref<StoreBrief[]>([])
const showSwitcher = computed(() => auth.isBoss || auth.role === 'admin')
const currentStoreName = ref<string>('')

async function loadStores() {
  if (!showSwitcher.value) return
  try {
    const res = await storeAPI.listAll()
    stores.value = res.data.data
    const cur = stores.value.find((s) => s.is_current)
    currentStoreName.value = cur?.name || ''
  } catch (e) {
    // 静默失败，不影响页面渲染
  }
}

async function onSwitchStore(storeId: string, storeName: string) {
  try {
    await ElMessageBox.confirm(
      `确定要切换到「${storeName}」吗？切换后只能看到该门店的数据。`,
      '切换门店',
      { confirmButtonText: '切换', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return // 用户取消
  }
  try {
    const res = await switchStore(storeId)
    const data = res.data.data
    // 更新本地 token 和用户信息（保留 role/user/employee，换 store_id）
    auth.setAuth(data.access_token, {
      ...auth.info,
      store_id: data.store_id,
    })
    currentStoreName.value = data.store_name
    stores.value = stores.value.map((s) => ({
      ...s,
      is_current: s.id === data.store_id,
    }))
    ElMessage.success(`已切换到「${data.store_name}」`)
    // 刷新当前页面数据
    window.location.reload()
  } catch (e: any) {
    ElMessage.error(e?.message || '切换失败')
  }
}

onMounted(() => {
  loadStores()
})

function back() {
  router.back()
}

// 判断是否是 Tab 首页（不需要返回箭头）
function isTabPage(path: string) {
  return ['/daily', '/management', '/settings', '/profile'].some(
    (p) => path === p || path === p + '/'
  )
}
</script>

<template>
  <div class="app-shell">
    <header class="shell-header">
      <div class="header-left">
        <span v-if="showBack || !isTabPage(route.path)" class="back-btn" @click="back">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M13 4l-6 6 6 6"/>
          </svg>
        </span>
      </div>
      <h1 class="shell-title">{{ title }}</h1>
      <div class="header-right">
        <!-- 切换门店下拉（仅 boss/admin 显示） -->
        <el-dropdown
          v-if="showSwitcher && stores.length > 0"
          trigger="click"
          @command="(cmd: string) => { const s = stores.find(x => x.id === cmd); if (s) onSwitchStore(s.id, s.name) }"
        >
          <span class="store-switcher">
            {{ currentStoreName || '切换门店' }}
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M2 3.5l3 3 3-3"/>
            </svg>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="s in stores"
                :key="s.id"
                :command="s.id"
                :disabled="s.is_current"
              >
                {{ s.name }}<span v-if="s.is_current" class="cur-tag">当前</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <img v-else src="/crush-ip.png" class="header-ip" alt="Crush" />
      </div>
    </header>
    <main class="shell-main">
      <slot />
    </main>
    <BottomNav />
  </div>
</template>

<style scoped lang="scss">
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.shell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  min-height: 48px;
  /* 毛玻璃效果 */
  background: rgba(17, 17, 17, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-left {
  width: 40px;
  display: flex;
  align-items: center;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
  -webkit-tap-highlight-color: transparent;

  &:active {
    background-color: rgba(255, 255, 255, 0.1);
    transform: scale(0.92);
  }
}

.shell-title {
  font-size: 16px;
  font-weight: 600;
  color: $brand-white;
  margin: 0;
  text-align: center;
  flex: 1;
}

.header-right {
  min-width: 40px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.store-switcher {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.1);
  color: $brand-white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: background-color 0.2s;
  -webkit-tap-highlight-color: transparent;

  &:active {
    background-color: rgba(255, 255, 255, 0.2);
  }
}

.cur-tag {
  margin-left: 6px;
  font-size: 11px;
  color: $brand-primary;
}

.header-ip {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  object-fit: contain;
}

.shell-main {
  flex: 1;
  padding-bottom: 88px;
}
</style>
