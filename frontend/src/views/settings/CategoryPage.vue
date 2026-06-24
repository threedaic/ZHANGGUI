<template>
  <div class="category-page">

    <h2 class="cat-title">{{ category.title }}</h2>
    <p class="cat-desc">服务对象：{{ category.target }}</p>

    <div class="item-list">
      <button
        v-for="item in category.items"
        :key="item.name"
        class="item-row"
        @click="item.path && router.push(item.path)"
        :class="{ disabled: !item.path }"
      >
        <span class="item-icon" v-html="item.icon"></span>
        <div class="item-info">
          <span class="item-name">{{ item.name }}</span>
          <span class="item-desc">{{ item.desc }}</span>
        </div>
        <span class="item-status" :class="item.built ? 'built' : 'pending'">
          {{ item.built ? '已配置' : '待开发' }}
        </span>
        <svg v-if="item.path" width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

interface CategoryItem {
  name: string
  desc: string
  path: string | null
  icon: string
  built: boolean
}

interface Category {
  title: string
  target: string
  items: CategoryItem[]
}

const categories: Record<string, Category> = {
  store: {
    title: '店铺管理',
    target: '店铺本身',
    items: [
      {
        name: '门店信息',
        desc: '门店名称、编码、地址等基础信息',
        path: '/settings/store-info',
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><path d="M3 19h16"/><path d="M5 19V11l6-6 6 6v8"/></svg>',
        built: true,
      },
      {
        name: '排班规则',
        desc: '休息天数、节假日策略、自动排班',
        path: '/settings/schedule-rule',
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><rect x="2" y="3" width="18" height="16" rx="2"/><line x1="2" y1="8" x2="20" y2="8"/><line x1="8" y1="8" x2="8" y2="19"/></svg>',
        built: true,
      },
      {
        name: '企微配置',
        desc: '企业微信接入、通讯录同步',
        path: '/settings/wework',
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><circle cx="8" cy="9" r="3"/><circle cx="15" cy="9" r="3"/><path d="M2 18c0-3 3-5 6-5s6 2 6 5"/><path d="M13 13c2 0 5 1.5 5 5"/></svg>',
        built: true,
      },
      {
        name: '合同默认值',
        desc: '公司信息、薪资制度、合同发起权限',
        path: '/settings/contract-default',
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><path d="M4 2h9l5 5v12a2 2 0 01-2 2H4a2 2 0 01-2-2V4a2 2 0 012-2z"/><path d="M13 2v5h5"/><line x1="7" y1="11" x2="15" y2="11"/><line x1="7" y1="15" x2="15" y2="15"/></svg>',
        built: true,
      },
    ],
  },
  employee: {
    title: '员工管理',
    target: '员工',
    items: [
      {
        name: '角色管理',
        desc: '员工角色分配与权限设置',
        path: '/settings/role-manager',
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><circle cx="11" cy="8" r="3"/><path d="M5 19c0-4 3-7 6-7s6 3 6 7"/></svg>',
        built: true,
      },
      {
        name: '班次定义',
        desc: '白班、夜班等班次时间段设置',
        path: '/settings/shift-setting',
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><rect x="2" y="3" width="18" height="16" rx="2"/><line x1="2" y1="8" x2="20" y2="8"/><line x1="8" y1="8" x2="8" y2="19"/></svg>',
        built: true,
      },
      {
        name: '薪资规则',
        desc: '发薪日、KPI系数范围',
        path: '/settings/salary-rules',
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><path d="M11 2v18"/><path d="M7 6h8"/><path d="M7 11h8"/><path d="M6 16h10"/></svg>',
        built: true,
      },
      {
        name: 'KPI 模板',
        desc: '考核维度与评分标准',
        path: null,
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#7A7C80" stroke-width="1.5" stroke-linecap="round"><path d="M4 18l4-6 4 4 6-10"/></svg>',
        built: false,
      },
      {
        name: '考勤规则',
        desc: '迟到阈值、早退判定规则',
        path: null,
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#7A7C80" stroke-width="1.5" stroke-linecap="round"><circle cx="11" cy="11" r="8"/><path d="M11 7v4l3 3"/></svg>',
        built: false,
      },
    ],
  },
  business: {
    title: '经营管理',
    target: '客人',
    items: [
      {
        name: '桌号管理',
        desc: '桌位配置、包间设置',
        path: '/settings/tables',
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="12" y="3" width="7" height="7" rx="1"/><rect x="3" y="12" width="7" height="7" rx="1"/><rect x="12" y="12" width="7" height="7" rx="1"/></svg>',
        built: true,
      },
      {
        name: '订桌规则',
        desc: '预约时段、自动确认规则',
        path: null,
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#7A7C80" stroke-width="1.5" stroke-linecap="round"><rect x="2" y="3" width="18" height="16" rx="2"/><line x1="2" y1="8" x2="20" y2="8"/><path d="M8 1v4"/><path d="M14 1v4"/></svg>',
        built: false,
      },
      {
        name: '评分码',
        desc: '桌面评分码生成与低分预警',
        path: null,
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#7A7C80" stroke-width="1.5" stroke-linecap="round"><path d="M11 2l2.5 5.5L19 8.5l-4 4 1 6-5-2.5-5 2.5 1-6-4-4 5.5-1z"/></svg>',
        built: false,
      },
      {
        name: '存酒配置',
        desc: '到期提醒天数、存酒规则',
        path: null,
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#7A7C80" stroke-width="1.5" stroke-linecap="round"><path d="M8 2h6l2 6H6l2-6z"/><rect x="5" y="8" width="12" height="12" rx="1"/></svg>',
        built: false,
      },
      {
        name: '防飞单规则',
        desc: '异常检测阈值、预警设置',
        path: null,
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#7A7C80" stroke-width="1.5" stroke-linecap="round"><path d="M11 3l8 15H3l8-15z"/><line x1="11" y1="9" x2="11" y2="13"/><circle cx="11" cy="15.5" r="0.5" fill="#7A7C80"/></svg>',
        built: false,
      },
    ],
  },
  system: {
    title: '系统设置',
    target: '系统本身',
    items: [
      {
        name: '推送设置',
        desc: '消息类型、推送渠道、群机器人、接收人配置',
        path: '/settings/notification',
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><path d="M11 2v3"/><path d="M5 11c0-4 3-7 6-7s6 3 6 7v5H5v-5z"/><path d="M9 17c0 1 1 3 2 3s2-2 2-3"/></svg>',
        built: true,
      },
      {
        name: 'AI 配置',
        desc: '小C模型、API地址、温度参数',
        path: '/settings/ai-config',
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><circle cx="11" cy="11" r="6"/><path d="M11 8v6"/><path d="M8 11h6"/></svg>',
        built: true,
      },
      {
        name: '打印设置',
        desc: '云打印机品牌、设备号、密钥配置',
        path: '/settings/printer',
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><rect x="4" y="5" width="14" height="8" rx="1"/><path d="M7 5V3a1 1 0 011-1h6a1 1 0 011 1v2"/><path d="M6 14h10"/><line x1="9" y1="11" x2="14" y2="11"/></svg>',
        built: true,
      },
      {
        name: '操作日志',
        desc: '所有数据修改记录',
        path: '/management/audit',
        icon: '<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><rect x="3" y="2" width="14" height="18" rx="1"/><line x1="7" y1="6" x2="13" y2="6"/><line x1="7" y1="10" x2="13" y2="10"/><line x1="7" y1="14" x2="10" y2="14"/></svg>',
        built: true,
      },
    ],
  },
}

const category = computed(() => {
  const cat = route.query.cat as string
  return categories[cat] || categories.store
})
</script>

<style scoped>
.category-page {
  padding: 16px;
  padding-bottom: calc(64px + 24px);
}

.cat-title {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 22px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0 0 4px;
}

.cat-desc {
  font-size: 12px;
  color: #7A7C80;
  margin: 0 0 20px;
}

.item-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.2s;
  text-align: left;
  width: 100%;
}

.item-row:hover {
  border-color: #FB0079;
}

.item-row.disabled {
  opacity: 0.6;
  cursor: default;
}

.item-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-name {
  display: block;
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 500;
  color: #C8C8C8;
}

.item-desc {
  display: block;
  font-size: 11px;
  color: #7A7C80;
  margin-top: 2px;
}

.item-status {
  flex-shrink: 0;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
}

.item-status.built {
  color: #4CAF50;
  background: rgba(76, 175, 80, 0.1);
}

.item-status.pending {
  color: #7A7C80;
  background: rgba(122, 124, 128, 0.1);
}
</style>
