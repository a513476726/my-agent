import Antd from "ant-design-vue";
import "ant-design-vue/dist/reset.css";
import { createPinia } from "pinia";
import { createApp } from "vue";

import App from "./App.vue";
import { setupDirectives } from "./directives";
import { router } from "./router";
import "./styles/main.css";
import { setupApiClient } from "./utils/request";

const app = createApp(App);

setupApiClient();
app.use(createPinia());
app.use(router);
app.use(Antd);
setupDirectives(app);
app.mount("#app");
