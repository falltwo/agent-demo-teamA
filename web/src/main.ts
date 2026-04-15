import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./assets/direction-a-tokens.css";
import "./assets/app-components.css";
import "./assets/skeleton.css";

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount("#app");
