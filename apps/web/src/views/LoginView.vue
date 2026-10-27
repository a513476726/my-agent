<script setup lang="ts">
import { LockOutlined, UserOutlined } from "@ant-design/icons-vue";
import type { FormInstance } from "ant-design-vue";
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useAuthStore } from "@/stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const formRef = ref<FormInstance>();
const loading = ref(false);
const form = reactive({ username: "", password: "" });
const rules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

function resolveRedirect(): string {
  const redirect = route.query.redirect;
  const value = Array.isArray(redirect) ? redirect[0] : redirect;
  if (typeof value === "string" && value.startsWith("/") && !value.startsWith("//")) {
    return value;
  }
  return "/";
}

async function handleSubmit(): Promise<void> {
  loading.value = true;
  try {
    await authStore.login(form.username.trim(), form.password);
    await router.replace(resolveRedirect());
  } catch {
    form.password = "";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-intro">
      <div class="intro-badge">内网工作台</div>
      <h1>把需求、代码与沉淀串成一条闭环</h1>
      <p>
        统一检索项目文档，阅读每日代码总结，并把可复用的工程经验沉淀为可追溯的知识。
      </p>
      <ul>
        <li>按项目隔离的文档与代码上下文</li>
        <li>日报、周报与季报统一入库</li>
        <li>回答与结论保留可定位出处</li>
      </ul>
    </section>

    <a-card class="login-card" :bordered="false">
      <div class="login-card__title">
        <h2>登录</h2>
        <p>个人工作助理 Agent 平台</p>
      </div>

      <a-form
        ref="formRef"
        :model="form"
        :rules="rules"
        layout="vertical"
        @finish="handleSubmit"
      >
        <a-form-item label="用户名" name="username">
          <a-input
            v-model:value="form.username"
            size="large"
            autocomplete="username"
            placeholder="请输入用户名"
          >
            <template #prefix><UserOutlined /></template>
          </a-input>
        </a-form-item>

        <a-form-item label="密码" name="password">
          <a-input-password
            v-model:value="form.password"
            size="large"
            autocomplete="current-password"
            placeholder="请输入密码"
          >
            <template #prefix><LockOutlined /></template>
          </a-input-password>
        </a-form-item>

        <a-button type="primary" html-type="submit" size="large" block :loading="loading">
          进入工作台
        </a-button>
      </a-form>
    </a-card>
  </main>
</template>

<style scoped>
.login-page {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(360px, 0.9fr);
  gap: 72px;
  align-items: center;
  min-height: 100vh;
  padding: 56px 8vw;
  color: #f8fafc;
  background:
    radial-gradient(circle at 18% 20%, rgb(109 93 252 / 35%), transparent 34%),
    radial-gradient(circle at 80% 70%, rgb(29 69 221 / 30%), transparent 38%),
    #0b1220;
}

.intro-badge {
  display: inline-flex;
  padding: 6px 12px;
  margin-bottom: 24px;
  font-size: 12px;
  color: #c7d2fe;
  background: rgb(99 102 241 / 18%);
  border: 1px solid rgb(129 140 248 / 35%);
  border-radius: 999px;
}

.login-intro h1 {
  max-width: 620px;
  margin: 0 0 20px;
  font-size: clamp(36px, 5vw, 64px);
  line-height: 1.08;
  letter-spacing: -1.5px;
}

.login-intro p {
  max-width: 600px;
  margin: 0 0 28px;
  font-size: 16px;
  line-height: 1.8;
  color: #cbd5e1;
}

.login-intro ul {
  display: grid;
  gap: 12px;
  padding: 0;
  margin: 0;
  color: #cbd5e1;
  list-style: none;
}

.login-intro li::before {
  margin-right: 10px;
  color: #818cf8;
  content: "●";
}

.login-card {
  width: 100%;
  max-width: 440px;
  padding: 14px;
  border-radius: 24px;
  box-shadow: 0 32px 80px rgb(0 0 0 / 35%);
}

.login-card__title {
  margin-bottom: 24px;
}

.login-card__title h2 {
  margin: 0;
  font-size: 28px;
  color: #111827;
}

.login-card__title p {
  margin: 8px 0 0;
  color: #6b7280;
}

@media (max-width: 900px) {
  .login-page {
    grid-template-columns: 1fr;
    gap: 36px;
    padding: 40px 24px;
  }

  .login-intro h1 {
    font-size: 38px;
  }

  .login-card {
    max-width: none;
  }
}
</style>
