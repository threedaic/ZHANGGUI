import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/daily',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginPage.vue'),
    meta: { public: true },
  },
  {
    path: '/auth-callback',
    name: 'AuthCallback',
    component: () => import('@/views/AuthCallback.vue'),
    meta: { public: true },
  },

  // ==================== 日常端（所有角色）====================
  {
    path: '/daily',
    component: () => import('@/layouts/DailyLayout.vue'),
    children: [
      {
        path: '',
        name: 'DailyHome',
        component: () => import('@/views/HomePage.vue'),
      },
      {
        path: 'booking',
        name: 'DailyBooking',
        component: () => import('@/views/booking/index.vue'),
      },
      {
        path: 'wine',
        name: 'DailyWine',
        component: () => import('@/views/wine/index.vue'),
      },
      {
        path: 'approval',
        name: 'DailyApproval',
        component: () => import('@/views/approval/index.vue'),
      },
      {
        path: 'approval/:id',
        name: 'DailyApprovalDetail',
        component: () => import('@/views/approval/ApprovalDetail.vue'),
      },
      {
        path: 'approval/create',
        name: 'DailyApprovalCreate',
        component: () => import('@/views/approval/ApprovalForm.vue'),
      },
      {
        path: 'butler',
        name: 'DailyButler',
        component: () => import('@/views/butler/index.vue'),
      },
      {
        path: 'butler/session/:id',
        name: 'DailyButlerSession',
        component: () => import('@/views/butler/ClosingFlow.vue'),
      },
      {
        path: 'inbox',
        name: 'DailyInbox',
        component: () => import('@/views/inbox/Inbox.vue'),
      },
      {
        path: 'inbox/:id',
        name: 'DailySignDetail',
        component: () => import('@/views/inbox/SignDetail.vue'),
      },
      {
        path: 'attendance-detail',
        name: 'DailyAttendanceDetail',
        component: () => import('@/views/attendance/AttendanceDetail.vue'),
      },
      {
        path: 'game',
        name: 'DailyGame',
        component: () => import('@/views/game/index.vue'),
      },
    ],
  },

  // ==================== 管理端（店长/老板）====================
  {
    path: '/management',
    component: () => import('@/layouts/ManagementLayout.vue'),
    meta: { roles: ['admin', 'boss', 'store_manager', 'accountant', 'bar_manager', 'service_manager', 'kitchen_manager'] },
    children: [
      {
        path: '',
        name: 'ManagementHome',
        component: () => import('@/views/management/index.vue'),
      },
      // 排班与人
      {
        path: 'schedule-attendance',
        name: 'ScheduleAttendance',
        component: () => import('@/views/schedule/index.vue'),
      },
      {
        path: 'kpi',
        name: 'KpiManage',
        component: () => import('@/views/kpi/index.vue'),
      },
      // 工资与账期
      {
        path: 'payroll',
        name: 'PayrollMonthly',
        component: () => import('@/views/management/PayrollMonthly.vue'),
      },
      {
        path: 'payroll/:id',
        name: 'PayrollDetail',
        component: () => import('@/views/management/PayrollDetail.vue'),
      },
      {
        path: 'period',
        name: 'PeriodManage',
        component: () => import('@/views/management/PeriodManage.vue'),
      },
      {
        path: 'rankings',
        name: 'Rankings',
        component: () => import('@/views/management/Rankings.vue'),
      },
      // 数据与考核
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
      },
      {
        path: 'rating',
        name: 'RatingManage',
        component: () => import('@/views/rating/admin.vue'),
      },
      {
        path: 'contracts',
        name: 'Contracts',
        component: () => import('@/views/contracts/index.vue'),
      },
      {
        path: 'antifraud',
        name: 'Antifraud',
        component: () => import('@/views/antifraud/index.vue'),
      },
      {
        path: 'audit',
        name: 'AuditLog',
        component: () => import('@/views/audit/AuditLog.vue'),
      },
      // 店铺运营
      {
        path: 'butler',
        name: 'Butler',
        component: () => import('@/views/butler/ButlerManage.vue'),
      },
      {
        path: 'butler/config',
        name: 'ButlerConfig',
        component: () => import('@/views/settings/ButlerSetting.vue'),
      },
      {
        path: 'butler/history',
        name: 'ButlerHistory',
        component: () => import('@/views/butler/SessionHistory.vue'),
      },
      {
        path: 'butler/dashboard',
        name: 'ButlerDashboard',
        component: () => import('@/views/butler/Dashboard.vue'),
      },
      {
        path: 'butler/session/:id',
        name: 'ButlerSession',
        component: () => import('@/views/butler/ClosingFlow.vue'),
      },
      {
        path: 'tables',
        name: 'Tables',
        component: () => import('@/views/management/Tables.vue'),
      },
      {
        path: 'wine-inventory',
        name: 'WineInventory',
        component: () => import('@/views/management/WineRoster.vue'),
      },
      {
        path: 'wine-stocktake',
        name: 'WineStocktake',
        component: () => import('@/views/wine/StocktakeList.vue'),
      },
      {
        path: 'wine-stocktake/:id',
        name: 'WineStocktakeDetail',
        component: () => import('@/views/wine/StocktakeDetail.vue'),
      },
      {
        path: 'penalties',
        name: 'Penalties',
        component: () => import('@/views/penalty/PenaltyList.vue'),
      },
      {
        path: 'penalties/create',
        name: 'PenaltyCreate',
        component: () => import('@/views/penalty/CreatePenalty.vue'),
      },
      // 审批
      {
        path: 'approval',
        name: 'ApprovalList',
        component: () => import('@/views/approval/index.vue'),
      },
      {
        path: 'approval/:id',
        name: 'ApprovalDetail',
        component: () => import('@/views/approval/ApprovalDetail.vue'),
      },
      {
        path: 'approval/create',
        name: 'ApprovalCreate',
        component: () => import('@/views/approval/ApprovalForm.vue'),
      },
      // 订座
      {
        path: 'bookings',
        name: 'Bookings',
        component: () => import('@/views/booking/index.vue'),
      },
      // 通知
      {
        path: 'notifications',
        name: 'Notifications',
        component: () => import('@/views/notifications/index.vue'),
      },
    ],
  },

  // ==================== 设置端（老板）====================
  {
    path: '/settings',
    component: () => import('@/layouts/SettingsLayout.vue'),
    meta: { roles: ['boss', 'admin'] },
    children: [
      {
        path: '',
        name: 'SettingsHome',
        component: () => import('@/views/settings/index.vue'),
      },
      // 分类页（通用）
      {
        path: 'category/:cat',
        name: 'SettingsCategory',
        component: () => import('@/views/settings/CategoryPage.vue'),
      },
      // 工资项配置
      {
        path: 'payroll-config',
        name: 'PayrollConfig',
        component: () => import('@/views/settings/PayrollConfig.vue'),
      },
      {
        path: 'payroll-config/formula/:code?',
        name: 'FormulaEditor',
        component: () => import('@/views/settings/FormulaEditor.vue'),
      },
      // 店铺管理
      {
        path: 'store-info',
        name: 'StoreInfo',
        component: () => import('@/views/settings/StoreInfo.vue'),
      },
      {
        path: 'store-config',
        name: 'StoreConfig',
        component: () => import('@/views/settings/StoreConfig.vue'),
      },
      {
        path: 'wework',
        name: 'WeworkSetting',
        component: () => import('@/views/settings/WeworkSetting.vue'),
      },
      {
        path: 'tables',
        name: 'TablesSetting',
        component: () => import('@/views/settings/TablesSetting.vue'),
      },
      // 排班规则
      {
        path: 'schedule-rule',
        name: 'ScheduleRuleSetting',
        component: () => import('@/views/settings/ScheduleRuleSetting.vue'),
      },
      {
        path: 'shift-setting',
        name: 'ShiftSetting',
        component: () => import('@/views/settings/ShiftSetting.vue'),
      },
      // 合同配置
      {
        path: 'contract-default',
        name: 'ContractDefault',
        component: () => import('@/views/settings/ContractDefault.vue'),
      },
      {
        path: 'contract-config',
        name: 'ContractConfig',
        component: () => import('@/views/settings/ContractConfig.vue'),
      },
      // 薪酬规则
      {
        path: 'salary-rules',
        name: 'SalaryRulesSetting',
        component: () => import('@/views/settings/SalaryRulesSetting.vue'),
      },
      // 管家设置
      {
        path: 'butler',
        name: 'ButlerSetting',
        component: () => import('@/views/settings/ButlerSetting.vue'),
      },
      {
        path: 'butler-template',
        name: 'ButlerTemplateEditor',
        component: () => import('@/views/settings/ButlerTemplateEditor.vue'),
      },
      // 角色管理
      {
        path: 'role-manager',
        name: 'RoleManager',
        component: () => import('@/views/settings/RoleManager.vue'),
      },
      // AI 配置
      {
        path: 'ai-config',
        name: 'AIConfig',
        component: () => import('@/views/settings/AIConfig.vue'),
      },
      // 通知设置
      {
        path: 'notification',
        name: 'NotificationSetting',
        component: () => import('@/views/settings/NotificationSetting.vue'),
      },
      // 打印机
      {
        path: 'printer',
        name: 'PrinterSetting',
        component: () => import('@/views/settings/PrinterManagement.vue'),
      },
    ],
  },

  // ==================== 员工端（我的）====================
  {
    path: '/profile',
    component: () => import('@/layouts/ProfileLayout.vue'),
    children: [
      {
        path: '',
        name: 'ProfileHome',
        component: () => import('@/views/profile/ProfileHome.vue'),
      },
      {
        path: 'my-data',
        name: 'MyData',
        component: () => import('@/views/profile/MyData.vue'),
      },
      {
        path: 'my-payroll/:id',
        name: 'MyPayrollDetail',
        component: () => import('@/views/profile/MyPayrollDetail.vue'),
      },
      {
        path: 'my-schedule',
        name: 'MySchedule',
        component: () => import('@/views/schedule/MySchedule.vue'),
      },
      {
        path: 'my-contract',
        name: 'MyContract',
        component: () => import('@/views/profile/MyContract.vue'),
      },
      {
        path: 'approval',
        name: 'MyApproval',
        component: () => import('@/views/approval/index.vue'),
      },
      {
        path: 'approval/:id',
        name: 'MyApprovalDetail',
        component: () => import('@/views/approval/ApprovalDetail.vue'),
      },
      {
        path: 'approval/create',
        name: 'MyApprovalCreate',
        component: () => import('@/views/approval/ApprovalForm.vue'),
      },
      {
        path: 'inbox',
        name: 'Inbox',
        component: () => import('@/views/inbox/Inbox.vue'),
      },
      {
        path: 'inbox/:id',
        name: 'SignDetail',
        component: () => import('@/views/inbox/SignDetail.vue'),
      },
      {
        path: 'rating',
        name: 'RatingSubmit',
        component: () => import('@/views/rating/index.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()
  // 公开路由放行
  if (to.meta.public) {
    return next()
  }
  // 未登录跳登录
  if (!auth.isLoggedIn) {
    return next({ name: 'Login' })
  }
  // 角色校验
  const allowed = to.meta.roles as string[] | undefined
  if (allowed && !allowed.includes(auth.role)) {
    return next({ name: 'ProfileHome' })
  }
  next()
})

export default router
