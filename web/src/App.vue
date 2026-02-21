<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { RoutePathEnum } from './constant';
import { getStorage } from './lib/session';

const router = useRouter();

onMounted(() => {
  const isLoggedIn = getStorage('isLoggedIn');

  console.log('isLoggedIn:', isLoggedIn);
  
  if(isLoggedIn) {
    router.push(RoutePathEnum.Home);
  } else {
    router.push(RoutePathEnum.Auth);
  }
});
</script>

<template>
  <router-view />
</template>
