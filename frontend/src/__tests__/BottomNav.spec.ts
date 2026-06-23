import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import BottomNav from '@/components/BottomNav.vue'

// Mock notification API to prevent XHR errors in test
vi.mock('@/api/notifications', () => ({
  notificationAPI: {
    getUnreadCount: vi.fn().mockResolvedValue({ data: { data: { count: 0 } } }),
  },
}))

describe('BottomNav', () => {
  const mountBottomNav = (tab = 'daily') => {
    const pinia = createPinia()
    setActivePinia(pinia)
    return mount(BottomNav, {
      props: { currentTab: tab },
      global: { plugins: [pinia] },
    })
  }

  it('renders without errors', () => {
    const wrapper = mountBottomNav()
    expect(wrapper.find('.bottom-nav').exists()).toBe(true)
  })

  it('renders at least 1 tab', () => {
    const wrapper = mountBottomNav()
    const items = wrapper.findAll('.nav-item')
    expect(items.length).toBeGreaterThanOrEqual(1)
  })

  it('highlights the active tab (daily)', () => {
    const wrapper = mountBottomNav('daily')
    const activeItem = wrapper.find('.nav-item.active')
    expect(activeItem.exists()).toBe(true)
  })
})
