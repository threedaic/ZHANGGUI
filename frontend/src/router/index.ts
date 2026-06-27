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

  // ==================== 总店端（系统管理员）====================
  {
    path: '/hq',
    component: () => import('@/layouts/HqLayout.vue'),
    meta: { roles: ['system_admin'] },
    children: [
      {
        path: '',
        name: 'HQHome',
        component: () => import('@/views/hq/index.vue'),
      },
      {
        path: 'stores',
        name: 'HQStores',
        component: () => import('@/views/hq/Stores.vue'),
      },
      {
        path: 'employees',
        name: 'HQEmployees',
        component: () => import('@/views/hq/Employees.vue'),
      },
      {
        path: 'ai-config',
        name: 'HQAIConfig',
        component: () => import('@/views/hq/AIConfig.vue'),
      },
    ],
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
        path: 'tasks',
        name: 'DailyTaskCenter',
        component: () => import('@/views/daily/TaskCenter.vue'),
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
      {
        path: 'checkin',
        name: 'DailyCheckin',
        component: () => import('@/views/checkin/index.vue'),
      },
      {
        path: 'my-payroll-preview',
        name: 'MyPayrollPreview',
        component: () => import('@/views/profile/MyPayrollPreview.vue'),
      },
    ],
  },

  // ==================== 管理端（店长/老板）====================
  {
    path: '/management',
    component: () => import('@/layouts/ManagementLayout.vue'),
    meta: { roles: ['system_admin', 'admin', 'boss', 'store_manager', 'accountant', 'bar_manager', 'service_manager', 'kitchen_manager'] },
    children: [
      {
        path: '',
        name: 'ManagementHome',
        component: () => import('@/views/management/index.vue'),
      },
      // 排班与人
      {
        path: 'schedule',
        name: 'ScheduleManage',
        component: () => import('@/views/schedule/index.vue'),
      },
      {
        path: 'attendance',
        name: 'AttendanceManage',
        component: () => import('@/views/attendance/index.vue'),
      },
      {
        path: 'kpi',
        name: 'KpiManage',
        component: () => import('@/views/kpi/index.vue'),
      },
      // 自动发薪（管理端：会计日常使用，无权限设置）
      {
        path: 'auto-payroll',
        name: 'AutoPayrollManage',
        component: () => import('@/views/management/AutoPayroll.vue'),
        meta: { roles: ['system_admin', 'boss', 'admin', 'accountant'] },
      },
      {
        path: 'auto-payroll/contract',
        name: 'AutoPayrollContractManage',
        component: () => import('@/views/management/payroll/ContractDetail.vue'),
        meta: { roles: ['system_admin', 'boss', 'admin', 'accountant'] },
      },
      {
        path: 'auto-payroll/performance',
        name: 'AutoPayrollPerformanceManage',
        component: () => import('@/views/management/payroll/PerformanceDetail.vue'),
        meta: { roles: ['system_admin', 'boss', 'admin', 'accountant'] },
      },
      {
        path: 'auto-payroll/attendance',
        name: 'AutoPayrollAttendanceManage',
        component: () => import('@/views/management/payroll/AttendanceDetail.vue'),
        meta: { roles: ['system_admin', 'boss', 'admin', 'accountant'] },
      },
      {
        path: 'auto-payroll/kpi',
        name: 'AutoPayrollKpiManage',
        component: () => import('@/views/management/payroll/KpiDetail.vue'),
        meta: { roles: ['system_admin', 'boss', 'admin', 'accountant'] },
      },
      {
        path: 'auto-payroll/reward_penalty',
        name: 'AutoPayrollRewardPenaltyManage',
        component: () => import('@/views/management/payroll/RewardPenaltyDetail.vue'),
        meta: { roles: ['system_admin', 'boss', 'admin', 'accountant'] },
      },
      {
        path: 'auto-payroll/overtime',
        name: 'AutoPayrollOvertimeManage',
        component: () => import('@/views/management/payroll/OvertimeDetail.vue'),
        meta: { roles: ['system_admin', 'boss', 'admin', 'accountant'] },
      },
      // 工资与账期
      {
        path: 'disputes',
        name: 'DisputeInbox',
        component: () => import('@/views/management/DisputeInbox.vue'),
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
      // OA任务
      {
        path: 'tasks',
        name: 'OATasks',
        component: () => import('@/views/tasks/index.vue'),
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
    meta: { roles: ['system_admin', 'boss', 'admin'] },
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
      // 经营管理规则
      {
        path: 'booking-rule',
        name: 'BookingRuleSetting',
        component: () => import('@/views/settings/BookingRuleSetting.vue'),
      },
      {
        path: 'rating-code',
        name: 'RatingCodeSetting',
        component: () => import('@/views/settings/RatingCodeSetting.vue'),
      },
      {
        path: 'wine-storage',
        name: 'WineStorageSetting',
        component: () => import('@/views/settings/WineStorageSetting.vue'),
      },
      {
        path: 'antifraud-rule',
        name: 'AntifraudRuleSetting',
        component: () => import('@/views/settings/AntifraudRuleSetting.vue'),
      },
      // 排班规则（已合并到排班设置，老书签自动跳转）
      {
        path: 'schedule-rule',
        redirect: { name: 'ShiftSetting' },
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
        path: 'auto-payroll',
        name: 'AutoPayroll',
        component: () => import('@/views/management/AutoPayroll.vue'),
        meta: { roles: ['system_admin', 'boss', 'admin', 'accountant'] },
      },
      // 自动发薪 - 模块二级页面
      {
        path: 'auto-payroll/contract',
        name: 'AutoPayrollContract',
        component: () => import('@/views/management/payroll/ContractDetail.vue'),
        meta: { roles: ['system_admin', 'boss', 'admin', 'accountant'] },
      },
      {
        path: 'auto-payroll/performance',
        name: 'AutoPayrollPerformance',
        component: () => import('@/views/management/payroll/PerformanceDetail.vue'),
        meta: { roles: ['system_admin', 'boss', 'admin', 'accountant'] },
      },
      {
        path: 'auto-payroll/attendance',
        name: 'AutoPayrollAttendance',
        component: () => import('@/views/management/payroll/AttendanceDetail.vue'),
        meta: { roles: ['system_admin', 'boss', 'admin', 'accountant'] },
      },
      {
        path: 'auto-payroll/kpi',
        name: 'AutoPayrollKpi',
        component: () => import('@/views/management/payroll/KpiDetail.vue'),
        meta: { roles: ['system_admin', 'boss', 'admin', 'accountant'] },
      },
      {
        path: 'auto-payroll/reward_penalty',
        name: 'AutoPayrollRewardPenalty',
        component: () => import('@/views/management/payroll/RewardPenaltyDetail.vue'),
        meta: { roles: ['system_admin', 'boss', 'admin', 'accountant'] },
      },
      {
        path: 'auto-payroll/overtime',
        name: 'AutoPayrollOvertime',
        component: () => import('@/views/management/payroll/OvertimeDetail.vue'),
        meta: { roles: ['system_admin', 'boss', 'admin', 'accountant'] },
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
      // 打卡设置
      {
        path: 'checkin',
        name: 'CheckinSetting',
        component: () => import('@/views/settings/CheckinSetting.vue'),
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
        path: 'my-disputes',
        name: 'MyDisputes',
        component: () => import('@/views/profile/MyDisputes.vue'),
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
