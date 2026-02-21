import { createMemoryHistory, createRouter } from "vue-router";
import Auth from "./pages/Auth.vue";
import Home from "./pages/Home.vue";
import { RoutePathEnum } from "./constant";

const routes = [
  { path: RoutePathEnum.Auth, component: Auth },
  { path: RoutePathEnum.Home, component: Home },
];

export const router = createRouter({
  history: createMemoryHistory(),
  routes,
});
