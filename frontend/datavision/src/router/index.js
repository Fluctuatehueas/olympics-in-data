import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/overview' },
  { path: '/overview', name: 'overview', component: () => import('../views/OverviewView.vue'), meta: { title: '总览' } },
  { path: '/medals', name: 'medals', component: () => import('../views/MedalsView.vue'), meta: { title: '奖牌格局' } },
  { path: '/countries', name: 'countries', component: () => import('../views/CountriesView.vue'), meta: { title: '国家兴衰' } },
  { path: '/gender', name: 'gender', component: () => import('../views/GenderView.vue'), meta: { title: '她的奥运' } },
  { path: '/sports', name: 'sports', component: () => import('../views/SportsView.vue'), meta: { title: '项目演化' } },
  { path: '/caliber', name: 'caliber', component: () => import('../views/CaliberView.vue'), meta: { title: '口径的魔力' } },
  { path: '/host', name: 'host', component: () => import('../views/HostView.vue'), meta: { title: '东道主效应' } },
  { path: '/small-teams', name: 'small-teams', component: () => import('../views/SmallTeamsView.vue'), meta: { title: '小团突破' } }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.afterEach((to) => {
  document.title = `${to.meta.title || '看板'} · 数说奥运 1896–2024`
})

export default router
