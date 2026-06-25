<template>
  <div class="printer-mgmt-page">
    <div class="page-header">
      <h1 class="page-title">打印机管理</h1>
      <span class="page-subtitle">统一管理打印机和打印路由</span>
    </div>

    <!-- Tab切换 -->
    <div class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- 模块打印配置 -->
    <div v-if="activeTab === 'modules'" class="tab-content">
      <div class="section-header">
        <h2 class="section-title">模块打印配置</h2>
        <span class="section-desc">配置哪些场景需要打印，哪些不需要</span>
      </div>

      <div class="module-config-list">
        <div
          v-for="config in moduleConfigs"
          :key="config.config_id"
          class="module-config-card"
        >
          <div class="module-config-header">
            <div class="module-config-info">
              <div class="module-config-name">{{ config.scene_name }}</div>
              <div class="module-config-desc">{{ config.description }}</div>
            </div>
            <div class="module-config-toggle">
              <label class="toggle-switch">
                <input
                  type="checkbox"
                  :checked="config.enabled"
                  @change="toggleModuleConfig(config)"
                />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
          <div class="module-config-detail">
            <span class="detail-tag">{{ moduleLabels[config.module_code] || config.module_code }}</span>
            <span class="detail-tag">{{ typeLabels[config.printer_type] }}</span>
            <span class="detail-tag">{{ triggerLabels[config.trigger_event] }}</span>
          </div>
          <div class="module-config-printer" v-if="config.enabled">
            <label class="form-label">指定打印机：</label>
            <select
              v-model="config.printer_id"
              class="form-input-sm"
              @change="updateModuleConfigPrinter(config)"
            >
              <option value="">自动选择（按类型）</option>
              <option
                v-for="p in printers"
                :key="p.printer_id"
                :value="p.printer_id"
              >
                {{ p.name }}
              </option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- 打印机列表 -->
    <div v-if="activeTab === 'printers'" class="tab-content">
      <div class="section-header">
        <h2 class="section-title">打印机列表</h2>
        <button class="add-btn" @click="showAddPrinter = true">+ 添加打印机</button>
      </div>

      <!-- 推荐提示卡片 -->
      <div class="recommend-card">
        <div class="recommend-icon">易</div>
        <div class="recommend-content">
          <div class="recommend-title">推荐使用易联云打印机</div>
          <div class="recommend-desc">
            稳定可靠 | 全国覆盖 | 无需本地网络 | 支持多种打印场景
          </div>
          <div class="recommend-steps">
            <span class="step">1. 购买易联云打印机</span>
            <span class="step-arrow">→</span>
            <span class="step">2. 注册开放平台账号</span>
            <span class="step-arrow">→</span>
            <span class="step">3. 获取密钥配置</span>
          </div>
        </div>
        <a href="https://www.10ss.net/open/" target="_blank" class="recommend-link">
          查看教程 →
        </a>
      </div>

      <div class="printer-list">
        <div
          v-for="printer in printers"
          :key="printer.printer_id"
          class="printer-card"
        >
          <div class="printer-info">
            <div class="printer-icon" :class="printer.printer_type">
              <span v-if="printer.printer_type === 'label'">标</span>
              <span v-else-if="printer.printer_type === 'receipt'">票</span>
              <span v-else>单</span>
            </div>
            <div class="printer-detail">
              <div class="printer-name">{{ printer.name }}</div>
              <div class="printer-meta">
                <span class="printer-type">{{ typeLabels[printer.printer_type] }}</span>
                <span class="printer-sn" v-if="printer.device_sn">SN: {{ printer.device_sn }}</span>
              </div>
            </div>
          </div>
          <div class="printer-status">
            <span class="status-dot" :class="{ online: printer.online_status }"></span>
            <span class="status-text">{{ printer.online_status ? '在线' : '离线' }}</span>
          </div>
          <div class="printer-actions">
            <button class="action-btn" @click="testPrint(printer)">测试</button>
            <button class="action-btn" @click="editPrinter(printer)">编辑</button>
            <button class="action-btn danger" @click="deletePrinter(printer)">删除</button>
          </div>
        </div>

        <div v-if="printers.length === 0" class="empty-state">
          暂无打印机，点击上方"添加打印机"开始配置
        </div>
      </div>
    </div>

    <!-- 路由规则 -->
    <div v-if="activeTab === 'routes'" class="tab-content">
      <div class="section-header">
        <h2 class="section-title">路由规则</h2>
        <button class="add-btn" @click="showAddRoute = true">+ 添加规则</button>
      </div>

      <div class="route-list">
        <div
          v-for="route in routes"
          :key="route.route_id"
          class="route-card"
        >
          <div class="route-info">
            <div class="route-name">{{ route.name }}</div>
            <div class="route-detail">
              <span class="route-trigger">{{ triggerLabels[route.trigger_event] }}</span>
              <span class="route-arrow">→</span>
              <span class="route-printer">{{ route.printer_name }}</span>
            </div>
          </div>
          <div class="route-meta">
            <span class="route-priority">优先级: {{ route.priority }}</span>
            <span class="route-status" :class="{ active: route.is_active }">
              {{ route.is_active ? '启用' : '禁用' }}
            </span>
          </div>
          <div class="route-actions">
            <button class="action-btn" @click="editRoute(route)">编辑</button>
            <button class="action-btn danger" @click="deleteRoute(route)">删除</button>
          </div>
        </div>

        <div v-if="routes.length === 0" class="empty-state">
          暂无路由规则，系统将按分类绑定或打印机类型自动路由
        </div>
      </div>
    </div>

    <!-- 分类绑定 -->
    <div v-if="activeTab === 'categories'" class="tab-content">
      <div class="section-header">
        <h2 class="section-title">分类打印机绑定</h2>
      </div>

      <div class="category-list">
        <div
          v-for="cat in categories"
          :key="cat.category_id"
          class="category-card"
        >
          <div class="category-name">{{ cat.name }}</div>
          <div class="category-printer">
            <label class="bind-label">出单打印机：</label>
            <select
              v-model="cat.printer_id"
              class="bind-select"
              @change="updateCategoryPrinter(cat)"
            >
              <option value="">使用默认</option>
              <option
                v-for="p in printers"
                :key="p.printer_id"
                :value="p.printer_id"
              >
                {{ p.name }} ({{ typeLabels[p.printer_type] }})
              </option>
            </select>
          </div>
          <div class="category-backup">
            <label class="bind-label">备用打印机：</label>
            <select
              v-model="cat.backup_printer_id"
              class="bind-select"
              @change="updateCategoryPrinter(cat)"
            >
              <option value="">无</option>
              <option
                v-for="p in printers"
                :key="p.printer_id"
                :value="p.printer_id"
              >
                {{ p.name }} ({{ typeLabels[p.printer_type] }})
              </option>
            </select>
          </div>
        </div>

        <div v-if="categories.length === 0" class="empty-state">
          暂无商品分类
        </div>
      </div>
    </div>

    <!-- 添加/编辑打印机弹窗 -->
    <div v-if="showAddPrinter || editingPrinter" class="modal-overlay" @click.self="closePrinterModal">
      <div class="modal-content">
        <h3 class="modal-title">{{ editingPrinter ? '编辑打印机' : '添加打印机' }}</h3>
        <div class="form-group">
          <label class="form-label">打印机名称</label>
          <input v-model="printerForm.name" class="form-input" placeholder="如：吧台出单机" />
        </div>
        <div class="form-group">
          <label class="form-label">打印机类型</label>
          <select v-model="printerForm.printer_type" class="form-input">
            <option value="label">标签机</option>
            <option value="receipt">小票机</option>
            <option value="order">出单机</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">打印机品牌</label>
          <select v-model="printerForm.brand" class="form-input">
            <option value="yilianyun">易联云</option>
            <option value="feie">飞鹅</option>
            <option value="xpyun">芯烨</option>
            <option value="gainscha">佳博</option>
            <option value="jolimark">映美云</option>
            <option value="zhongwu">中午云</option>
            <option value="ushengyun">优声云</option>
            <option value="kuaidi100">快递100</option>
            <option value="printcenter">365智能云打印</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">设备SN</label>
          <input v-model="printerForm.device_sn" class="form-input" placeholder="打印机背面贴纸上的设备号" />
        </div>
        <!-- 易联云：client_id + client_secret -->
        <template v-if="printerForm.brand === 'yilianyun'">
          <div class="form-group">
            <label class="form-label">应用ID (client_id)</label>
            <input v-model="printerForm.api_user" class="form-input" placeholder="易联云开放平台获取" />
          </div>
          <div class="form-group">
            <label class="form-label">应用密钥 (client_secret)</label>
            <input v-model="printerForm.api_secret" class="form-input" type="password" :placeholder="editingPrinter ? '留空表示不修改' : '易联云开放平台获取'" />
          </div>
        </template>
        <!-- 飞鹅：user + ukey -->
        <template v-else-if="printerForm.brand === 'feie'">
          <div class="form-group">
            <label class="form-label">账号 (user)</label>
            <input v-model="printerForm.api_user" class="form-input" placeholder="飞鹅云后台注册的账号" />
          </div>
          <div class="form-group">
            <label class="form-label">密钥 (ukey)</label>
            <input v-model="printerForm.api_secret" class="form-input" type="password" :placeholder="editingPrinter ? '留空表示不修改' : '飞鹅云后台生成的UKEY'" />
          </div>
        </template>
        <!-- 芯烨：user + userKey -->
        <template v-else-if="printerForm.brand === 'xpyun'">
          <div class="form-group">
            <label class="form-label">开发者ID (user)</label>
            <input v-model="printerForm.api_user" class="form-input" placeholder="芯烨云平台注册用户名" />
          </div>
          <div class="form-group">
            <label class="form-label">开发者密钥 (userKey)</label>
            <input v-model="printerForm.api_secret" class="form-input" type="password" :placeholder="editingPrinter ? '留空表示不修改' : '芯烨云开放平台获取'" />
          </div>
        </template>
        <!-- 佳博：memberCode + apiKey -->
        <template v-else-if="printerForm.brand === 'gainscha'">
          <div class="form-group">
            <label class="form-label">商户编码 (memberCode)</label>
            <input v-model="printerForm.api_user" class="form-input" placeholder="佳博云平台商户编码" />
          </div>
          <div class="form-group">
            <label class="form-label">API密钥 (apiKey)</label>
            <input v-model="printerForm.api_secret" class="form-input" type="password" :placeholder="editingPrinter ? '留空表示不修改' : '佳博云平台API密钥'" />
          </div>
        </template>
        <!-- 映美云：app_id + app_key -->
        <template v-else-if="printerForm.brand === 'jolimark'">
          <div class="form-group">
            <label class="form-label">应用ID (app_id)</label>
            <input v-model="printerForm.api_user" class="form-input" placeholder="映美云开放平台获取" />
          </div>
          <div class="form-group">
            <label class="form-label">应用密钥 (app_key)</label>
            <input v-model="printerForm.api_secret" class="form-input" type="password" :placeholder="editingPrinter ? '留空表示不修改' : '映美云开放平台获取'" />
          </div>
        </template>
        <!-- 中午云：appid + appsecret + deviceid + devicesecret -->
        <template v-else-if="printerForm.brand === 'zhongwu'">
          <div class="form-group">
            <label class="form-label">应用ID (appid)</label>
            <input v-model="printerForm.api_user" class="form-input" placeholder="中午云开放平台获取" />
          </div>
          <div class="form-group">
            <label class="form-label">应用密钥 (appsecret)</label>
            <input v-model="printerForm.api_secret" class="form-input" type="password" :placeholder="editingPrinter ? '留空表示不修改' : '中午云开放平台获取'" />
          </div>
          <div class="form-group">
            <label class="form-label">设备编号 (deviceid)</label>
            <input v-model="printerForm.device_sn" class="form-input" placeholder="打印机设备编号" />
          </div>
          <div class="form-group">
            <label class="form-label">设备密钥 (devicesecret)</label>
            <input v-model="printerForm.extra_config" class="form-input" type="password" placeholder="打印机设备密钥" />
          </div>
        </template>
        <!-- 优声云：appId + appSecret + deviceid + devicesecret -->
        <template v-else-if="printerForm.brand === 'ushengyun'">
          <div class="form-group">
            <label class="form-label">应用ID (appId)</label>
            <input v-model="printerForm.api_user" class="form-input" placeholder="优声云开放平台获取" />
          </div>
          <div class="form-group">
            <label class="form-label">应用密钥 (appSecret)</label>
            <input v-model="printerForm.api_secret" class="form-input" type="password" :placeholder="editingPrinter ? '留空表示不修改' : '优声云开放平台获取'" />
          </div>
          <div class="form-group">
            <label class="form-label">设备编号 (deviceid)</label>
            <input v-model="printerForm.device_sn" class="form-input" placeholder="打印机设备编号" />
          </div>
          <div class="form-group">
            <label class="form-label">设备密钥 (devicesecret)</label>
            <input v-model="printerForm.extra_config" class="form-input" type="password" placeholder="打印机设备密钥" />
          </div>
        </template>
        <!-- 快递100：key + secret -->
        <template v-else-if="printerForm.brand === 'kuaidi100'">
          <div class="form-group">
            <label class="form-label">应用Key</label>
            <input v-model="printerForm.api_user" class="form-input" placeholder="快递100开放平台获取" />
          </div>
          <div class="form-group">
            <label class="form-label">应用Secret</label>
            <input v-model="printerForm.api_secret" class="form-input" type="password" :placeholder="editingPrinter ? '留空表示不修改' : '快递100开放平台获取'" />
          </div>
        </template>
        <!-- 365智能云：deviceNo + key -->
        <template v-else-if="printerForm.brand === 'printcenter'">
          <div class="form-group">
            <label class="form-label">打印机编号 (deviceNo)</label>
            <input v-model="printerForm.api_user" class="form-input" placeholder="365智能云打印机编号" />
          </div>
          <div class="form-group">
            <label class="form-label">密钥 (key)</label>
            <input v-model="printerForm.api_secret" class="form-input" type="password" :placeholder="editingPrinter ? '留空表示不修改' : '365智能云打印机密钥'" />
          </div>
        </template>
        <div class="form-group">
          <label class="form-label">纸宽 (mm)</label>
          <select v-model.number="printerForm.paper_width" class="form-input">
            <option :value="58">58mm（窄纸/标签机）</option>
            <option :value="76">76mm</option>
            <option :value="80">80mm（标准/出单机）</option>
            <option :value="110">110mm（宽纸）</option>
          </select>
        </div>
        <div class="modal-actions">
          <button class="cancel-btn" @click="closePrinterModal">取消</button>
          <button class="confirm-btn" @click="savePrinter" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 添加/编辑路由规则弹窗 -->
    <div v-if="showAddRoute || editingRoute" class="modal-overlay" @click.self="closeRouteModal">
      <div class="modal-content">
        <h3 class="modal-title">{{ editingRoute ? '编辑路由规则' : '添加路由规则' }}</h3>
        <div class="form-group">
          <label class="form-label">规则名称</label>
          <input v-model="routeForm.name" class="form-input" placeholder="如：酒水→吧台" />
        </div>
        <div class="form-group">
          <label class="form-label">触发时机</label>
          <select v-model="routeForm.trigger_event" class="form-input">
            <option value="order_created">订单创建时</option>
            <option value="payment_completed">支付完成时</option>
            <option value="manual">手动重打</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">文档类型</label>
          <select v-model="routeForm.document_type" class="form-input">
            <option value="order">出单</option>
            <option value="receipt">收据</option>
            <option value="label">标签</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">匹配条件</label>
          <select v-model="routeForm.filter_type" class="form-input">
            <option value="all">全部订单</option>
            <option value="category">按商品分类</option>
            <option value="order_type">按订单类型</option>
          </select>
        </div>
        <div class="form-group" v-if="routeForm.filter_type === 'category'">
          <label class="form-label">选择分类</label>
          <div class="checkbox-group">
            <label v-for="cat in categories" :key="cat.category_id" class="checkbox-item">
              <input
                type="checkbox"
                :value="cat.category_id"
                v-model="selectedCategories"
              />
              {{ cat.name }}
            </label>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">目标打印机</label>
          <select v-model="routeForm.printer_id" class="form-input">
            <option value="">请选择</option>
            <option
              v-for="p in printers"
              :key="p.printer_id"
              :value="p.printer_id"
            >
              {{ p.name }} ({{ typeLabels[p.printer_type] }})
            </option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">优先级（数字越小越优先）</label>
          <input v-model.number="routeForm.priority" class="form-input" type="number" min="1" max="100" />
        </div>
        <div class="modal-actions">
          <button class="cancel-btn" @click="closeRouteModal">取消</button>
          <button class="confirm-btn" @click="saveRoute" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { printersAPI, type PrinterInfo, type PrintRoute, type CategoryPrinter, type PrinterForm, type PrintRouteForm, type ModulePrintConfig } from '@/api/printers'

const activeTab = ref('printers')
const saving = ref(false)

const tabs = [
  { key: 'printers', label: '打印机' },
  { key: 'routes', label: '路由规则' },
  { key: 'categories', label: '分类绑定' },
  { key: 'modules', label: '模块配置' },
]

const typeLabels: Record<string, string> = {
  label: '标签机',
  receipt: '小票机',
  order: '出单机',
}

const triggerLabels: Record<string, string> = {
  order_created: '订单创建',
  payment_completed: '支付完成',
  manual: '手动重打',
}

const moduleLabels: Record<string, string> = {
  wine_storage: '存酒管理',
  pos: '收银台',
  inventory: '库存管理',
  employee: '员工管理',
  booking: '预订管理',
}

// 打印机相关
const printers = ref<PrinterInfo[]>([])
const showAddPrinter = ref(false)
const editingPrinter = ref<PrinterInfo | null>(null)
const printerForm = reactive<PrinterForm>({
  name: '',
  printer_type: 'order',
  brand: 'yilianyun',
  device_sn: '',
  api_user: '',
  api_secret: '',
  paper_width: 80,
})

// 路由规则相关
const routes = ref<PrintRoute[]>([])
const showAddRoute = ref(false)
const editingRoute = ref<PrintRoute | null>(null)
const selectedCategories = ref<string[]>([])
const routeForm = reactive<PrintRouteForm>({
  name: '',
  trigger_event: 'order_created',
  document_type: 'order',
  filter_type: 'all',
  printer_id: '',
  priority: 1,
})

// 分类相关
const categories = ref<CategoryPrinter[]>([])

// 模块打印配置相关
const moduleConfigs = ref<ModulePrintConfig[]>([])

// 加载数据
async function loadPrinters() {
  try {
    const { data: res } = await printersAPI.list()
    if (res.code === 0) {
      printers.value = res.data || []
    }
  } catch (e: any) {
    ElMessage.error('加载打印机列表失败')
  }
}

async function loadRoutes() {
  try {
    const { data: res } = await printersAPI.listRoutes()
    if (res.code === 0) {
      routes.value = res.data || []
    }
  } catch (e: any) {
    ElMessage.error('加载路由规则失败')
  }
}

async function loadCategories() {
  try {
    const { data: res } = await printersAPI.listCategories()
    if (res.code === 0) {
      categories.value = res.data || []
    }
  } catch (e: any) {
    ElMessage.error('加载分类列表失败')
  }
}

async function loadModuleConfigs() {
  try {
    const { data: res } = await printersAPI.listModuleConfigs()
    if (res.code === 0) {
      moduleConfigs.value = res.data || []
    }
  } catch (e: any) {
    ElMessage.error('加载模块配置失败')
  }
}

// 打印机操作
function editPrinter(printer: PrinterInfo) {
  editingPrinter.value = printer
  printerForm.name = printer.name
  printerForm.printer_type = printer.printer_type
  printerForm.brand = printer.brand || 'yilianyun'
  printerForm.device_sn = printer.device_sn || ''
  printerForm.api_user = printer.api_user || ''
  printerForm.paper_width = printer.paper_width || 80
}

function closePrinterModal() {
  showAddPrinter.value = false
  editingPrinter.value = null
  printerForm.name = ''
  printerForm.printer_type = 'order'
  printerForm.brand = 'yilianyun'
  printerForm.device_sn = ''
  printerForm.api_user = ''
  printerForm.api_secret = ''
  printerForm.paper_width = 80
}

async function savePrinter() {
  if (!printerForm.name) {
    ElMessage.warning('请输入打印机名称')
    return
  }

  saving.value = true
  try {
    if (editingPrinter.value) {
      // 编辑模式：空密码不发送，避免覆盖原值
      const updateData: Record<string, any> = { ...printerForm }
      if (!updateData.api_secret) {
        delete updateData.api_secret
      }
      const { data: res } = await printersAPI.update(editingPrinter.value.printer_id, updateData as any)
      if (res.code === 0) {
        ElMessage.success('打印机更新成功')
        closePrinterModal()
        loadPrinters()
      } else {
        ElMessage.error(res.message || '更新失败')
      }
    } else {
      const { data: res } = await printersAPI.create(printerForm)
      if (res.code === 0) {
        ElMessage.success('打印机添加成功')
        closePrinterModal()
        loadPrinters()
      } else {
        ElMessage.error(res.message || '添加失败')
      }
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '操作失败')
  } finally {
    saving.value = false
  }
}

async function deletePrinter(printer: PrinterInfo) {
  try {
    await ElMessageBox.confirm(`确定删除打印机"${printer.name}"吗？`, '确认删除', {
      type: 'warning',
    })
    const { data: res } = await printersAPI.delete(printer.printer_id)
    if (res.code === 0) {
      ElMessage.success('打印机已删除')
      loadPrinters()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch {
    // 取消
  }
}

async function testPrint(printer: PrinterInfo) {
  try {
    const { data: res } = await printersAPI.test(printer.printer_id)
    if (res.code === 0) {
      const result = res.data || {}
      if (result.status === 'sent') {
        ElMessage.success('测试打印已发送，请检查打印机是否出纸')
      } else if (result.status === 'failed') {
        // 显示具体的失败原因
        ElMessage.error(result.message || '测试打印失败')
      } else {
        ElMessage.success('测试打印已发送')
      }
    } else {
      ElMessage.error(res.message || '测试打印失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || e?.response?.data?.detail || '测试打印失败')
  }
}

// 路由规则操作
function editRoute(route: PrintRoute) {
  editingRoute.value = route
  routeForm.name = route.name
  routeForm.trigger_event = route.trigger_event
  routeForm.document_type = route.document_type
  routeForm.filter_type = route.filter_type
  routeForm.printer_id = route.printer_id
  routeForm.priority = route.priority
  selectedCategories.value = route.filter_value?.category_ids || []
}

function closeRouteModal() {
  showAddRoute.value = false
  editingRoute.value = null
  routeForm.name = ''
  routeForm.trigger_event = 'order_created'
  routeForm.document_type = 'order'
  routeForm.filter_type = 'all'
  routeForm.printer_id = ''
  routeForm.priority = 1
  selectedCategories.value = []
}

async function saveRoute() {
  if (!routeForm.name) {
    ElMessage.warning('请输入规则名称')
    return
  }
  if (!routeForm.printer_id) {
    ElMessage.warning('请选择目标打印机')
    return
  }

  const formData = {
    ...routeForm,
    filter_value: routeForm.filter_type === 'category'
      ? { category_ids: selectedCategories.value }
      : undefined,
  }

  saving.value = true
  try {
    if (editingRoute.value) {
      const { data: res } = await printersAPI.updateRoute(editingRoute.value.route_id, formData)
      if (res.code === 0) {
        ElMessage.success('路由规则更新成功')
        closeRouteModal()
        loadRoutes()
      } else {
        ElMessage.error(res.message || '更新失败')
      }
    } else {
      const { data: res } = await printersAPI.createRoute(formData)
      if (res.code === 0) {
        ElMessage.success('路由规则添加成功')
        closeRouteModal()
        loadRoutes()
      } else {
        ElMessage.error(res.message || '添加失败')
      }
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '操作失败')
  } finally {
    saving.value = false
  }
}

async function deleteRoute(route: PrintRoute) {
  try {
    await ElMessageBox.confirm(`确定删除路由规则"${route.name}"吗？`, '确认删除', {
      type: 'warning',
    })
    const { data: res } = await printersAPI.deleteRoute(route.route_id)
    if (res.code === 0) {
      ElMessage.success('路由规则已删除')
      loadRoutes()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch {
    // 取消
  }
}

// 分类绑定操作
async function updateCategoryPrinter(cat: CategoryPrinter) {
  try {
    const { data: res } = await printersAPI.updateCategoryPrinter(cat.category_id, {
      printer_id: cat.printer_id || null,
      backup_printer_id: cat.backup_printer_id || null,
    })
    if (res.code === 0) {
      ElMessage.success('绑定更新成功')
    } else {
      ElMessage.error(res.message || '更新失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '更新失败')
  }
}

// 模块打印配置操作
async function toggleModuleConfig(config: ModulePrintConfig) {
  try {
    const { data: res } = await printersAPI.updateModuleConfig(config.config_id, {
      enabled: !config.enabled,
    })
    if (res.code === 0) {
      config.enabled = !config.enabled
      ElMessage.success(config.enabled ? '已启用' : '已禁用')
    } else {
      ElMessage.error(res.message || '操作失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '操作失败')
  }
}

async function updateModuleConfigPrinter(config: ModulePrintConfig) {
  try {
    const { data: res } = await printersAPI.updateModuleConfig(config.config_id, {
      printer_id: config.printer_id || null,
    })
    if (res.code === 0) {
      ElMessage.success('打印机绑定更新成功')
    } else {
      ElMessage.error(res.message || '更新失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '更新失败')
  }
}

// 初始化
onMounted(() => {
  loadPrinters()
  loadRoutes()
  loadCategories()
  loadModuleConfigs()
})
</script>

<style scoped>
.printer-mgmt-page {
  padding: 16px;
  background: #000000;
  min-height: 100vh;
  padding-bottom: calc(56px + 24px);
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 22px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0;
}

.page-subtitle {
  font-size: 12px;
  color: #7A7C80;
}

/* Tab切换 */
.tab-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 1px solid #222222;
  padding-bottom: 12px;
}

.tab-btn {
  padding: 8px 16px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #7A7C80;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn.active {
  background: #FB0079;
  border-color: #FB0079;
  color: #FFFFFF;
}

/* 区块头部 */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #FFFFFF;
  margin: 0;
}

.add-btn {
  padding: 8px 16px;
  background: #FB0079;
  border: none;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 13px;
  cursor: pointer;
}

/* 打印机卡片 */
.printer-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.printer-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
}

.printer-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.printer-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #222222;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #7A7C80;
}

.printer-icon.label {
  background: #1a237e;
  color: #8c9eff;
}

.printer-icon.receipt {
  background: #1b5e20;
  color: #81c784;
}

.printer-icon.order {
  background: #b71c1c;
  color: #ef9a9a;
}

.printer-detail {
  flex: 1;
}

.printer-name {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 4px;
}

.printer-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #7A7C80;
}

.printer-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-right: 16px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #7A7C80;
}

.status-dot.online {
  background: #4caf50;
}

.status-text {
  font-size: 12px;
  color: #7A7C80;
}

.printer-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 6px 12px;
  background: #222222;
  border: 1px solid #333333;
  border-radius: 6px;
  color: #C8C8C8;
  font-size: 12px;
  cursor: pointer;
}

.action-btn.danger {
  color: #ef5350;
}

/* 路由规则卡片 */
.route-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.route-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
}

.route-info {
  flex: 1;
}

.route-name {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 4px;
}

.route-detail {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #7A7C80;
}

.route-arrow {
  color: #FB0079;
}

.route-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  margin-right: 16px;
}

.route-priority {
  font-size: 12px;
  color: #7A7C80;
}

.route-status {
  font-size: 12px;
  color: #7A7C80;
}

.route-status.active {
  color: #4caf50;
}

.route-actions {
  display: flex;
  gap: 8px;
}

/* 分类绑定 */
.category-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.category-card {
  padding: 16px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
}

.category-name {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 12px;
}

.category-printer,
.category-backup {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.bind-label {
  font-size: 12px;
  color: #7A7C80;
  min-width: 80px;
}

.bind-select {
  flex: 1;
  height: 36px;
  padding: 0 12px;
  background: #0a0a0a;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 13px;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  width: 90%;
  max-width: 400px;
  max-height: 80vh;
  overflow-y: auto;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 16px;
  padding: 20px;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #FFFFFF;
  margin: 0 0 20px 0;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 12px;
  color: #7A7C80;
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  background: #0a0a0a;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 13px;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: #FB0079;
  outline: none;
}

.checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #C8C8C8;
}

.checkbox-item input {
  accent-color: #FB0079;
}

.modal-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.cancel-btn,
.confirm-btn {
  flex: 1;
  height: 44px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.cancel-btn {
  background: #222222;
  color: #C8C8C8;
}

.confirm-btn {
  background: #FB0079;
  color: #FFFFFF;
}

.confirm-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 推荐卡片 */
.recommend-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: linear-gradient(135deg, rgba(251, 0, 121, 0.08) 0%, rgba(251, 0, 121, 0.03) 100%);
  border: 1px solid rgba(251, 0, 121, 0.2);
  border-radius: 12px;
  margin-bottom: 16px;
}

.recommend-icon {
  width: 48px;
  height: 48px;
  background: #FB0079;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: #FFFFFF;
  flex-shrink: 0;
}

.recommend-content {
  flex: 1;
}

.recommend-title {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 4px;
}

.recommend-desc {
  font-size: 12px;
  color: #C8C8C8;
  margin-bottom: 8px;
}

.recommend-steps {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #7A7C80;
}

.step {
  padding: 2px 6px;
  background: rgba(251, 0, 121, 0.1);
  border: 1px solid rgba(251, 0, 121, 0.2);
  border-radius: 4px;
}

.step-arrow {
  color: #FB0079;
}

.recommend-link {
  padding: 8px 16px;
  background: #FB0079;
  border: none;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
  transition: opacity 0.2s;
}

.recommend-link:hover {
  opacity: 0.85;
}

/* 空状态 */
.empty-state {
  padding: 40px;
  text-align: center;
  font-size: 14px;
  color: #7A7C80;
  background: #111111;
  border: 1px dashed #333333;
  border-radius: 12px;
}

/* 区块描述 */
.section-desc {
  font-size: 12px;
  color: #7A7C80;
}

/* 模块打印配置 */
.module-config-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.module-config-card {
  padding: 16px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
}

.module-config-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.module-config-info {
  flex: 1;
}

.module-config-name {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 4px;
}

.module-config-desc {
  font-size: 12px;
  color: #7A7C80;
}

.module-config-toggle {
  margin-left: 16px;
}

/* 开关 */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #333333;
  transition: 0.3s;
  border-radius: 24px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: #7A7C80;
  transition: 0.3s;
  border-radius: 50%;
}

.toggle-switch input:checked + .toggle-slider {
  background-color: #FB0079;
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(20px);
  background-color: #FFFFFF;
}

.module-config-detail {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.detail-tag {
  padding: 4px 8px;
  background: #222222;
  border-radius: 4px;
  font-size: 12px;
  color: #7A7C80;
}

.module-config-printer {
  display: flex;
  align-items: center;
  gap: 8px;
}

.module-config-printer .form-label {
  margin-bottom: 0;
  white-space: nowrap;
}

.form-input-sm {
  flex: 1;
  height: 36px;
  padding: 0 12px;
  background: #0a0a0a;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 13px;
}
</style>
