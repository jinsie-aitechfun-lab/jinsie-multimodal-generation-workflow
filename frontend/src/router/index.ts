import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import LandingPage from '../components/landing/LandingPage.vue'
import StudioView from '../views/StudioView.vue'

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
