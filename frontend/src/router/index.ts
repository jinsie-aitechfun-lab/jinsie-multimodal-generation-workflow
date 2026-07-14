import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const LandingPage = () => import('../components/landing/LandingPage.vue')
const StudioView = () => import('../views/StudioView.vue')

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: LandingPage,
  },
  {
    path: '/studio',
    name: 'studio',
    component: StudioView,
  },
  // Anything else falls back to the landing page.
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router
