import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

import MainLayout from "@/layouts/MainLayout.vue";
import RouteGroupView from "@/layouts/RouteGroupView.vue";
import { useAuthStore } from "@/stores/auth";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/LoginView.vue"),
    meta: { title: "登录", public: true },
  },
  {
    path: "/",
    component: MainLayout,
    children: [
      {
        path: "",
        name: "Home",
        component: () => import("@/views/HomeView.vue"),
        meta: { title: "工作台", keepAlive: true },
      },
      {
        path: "project-space",
        component: RouteGroupView,
        redirect: "/project-space/projects",
        meta: { title: "项目空间" },
        children: [
          {
            path: "projects",
            name: "Projects",
            component: () => import("@/views/projects/ProjectListView.vue"),
            meta: { title: "项目管理", keepAlive: true },
          },
          {
            path: "documents",
            name: "Documents",
            component: () => import("@/views/documents/DocumentListView.vue"),
            meta: { title: "文档管理", keepAlive: true },
          },
          {
            path: "reports",
            name: "Reports",
            component: () => import("@/views/reports/ReportListView.vue"),
            meta: { title: "报告", keepAlive: true },
          },
        ],
      },
      {
        path: "operations",
        component: RouteGroupView,
        redirect: "/operations/capabilities",
        meta: { title: "运营管理" },
        children: [
          {
            path: "capabilities",
            name: "Capabilities",
            component: () => import("@/views/EmptyModuleView.vue"),
            meta: { title: "能力沉淀" },
          },
          {
            path: "jobs",
            name: "Jobs",
            component: () => import("@/views/EmptyModuleView.vue"),
            meta: { title: "任务" },
          },
          {
            path: "audit",
            name: "Audit",
            component: () => import("@/views/EmptyModuleView.vue"),
            meta: { title: "审计日志" },
          },
        ],
      },
    ],
  },
  {
    path: "/:pathMatch(.*)*",
    name: "NotFound",
    component: () => import("@/views/NotFoundView.vue"),
    meta: { title: "页面不存在", public: true },
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const authStore = useAuthStore();

  if (to.meta.public) {
    if (to.name === "Login" && authStore.hasToken) {
      return "/";
    }
    return true;
  }

  if (!authStore.hasToken) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }

  try {
    await authStore.ensureSession();
    return true;
  } catch {
    authStore.logout();
    return { path: "/login", query: { redirect: to.fullPath } };
  }
});

router.afterEach((to) => {
  document.title = `${String(to.meta.title || "工作台")} · 个人工作助理 Agent 平台`;
});

export default router;
