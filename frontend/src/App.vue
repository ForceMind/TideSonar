<template>
  <div class="h-screen w-screen flex flex-col bg-gray-900 overflow-hidden font-sans">
    <!-- Header -->
    <header class="h-12 bg-gray-800 border-b border-gray-700 flex items-center px-4 justify-between select-none">
      <div class="flex items-center space-x-2">
        <div class="w-3 h-3 rounded-full bg-blue-500 animate-pulse"></div>
        <h1 class="text-xl font-bold tracking-tight text-white">观潮 <span class="text-blue-500 font-light">TideSonar</span></h1>
      </div>
      <div class="text-xs text-gray-500 font-mono">
        状态: <span :class="wsStatusClass">{{ wsStatusText }}</span> | 捕捉异动数: {{ totalAlerts }}
      </div>
    </header>

    <!-- Main Content: 4 Columns -->
    <main class="flex-1 flex overflow-hidden divide-x divide-gray-700">
      
      <!-- Column 1: HS300 -->
      <div class="flex-1 flex flex-col min-w-0">
        <div class="h-10 bg-gray-800/80 backdrop-blur border-b border-gray-700 flex items-center justify-center">
            <h2 class="font-bold text-gray-200">沪深300 <span class="text-xs text-gray-500 font-normal">核心资产</span></h2>
        </div>
        <div class="flex-1 overflow-y-auto p-2 scrollbar-hide">
            <StockCard v-for="item in lists.HS300" :key="item.id" :data="item" />
        </div>
      </div>

      <!-- Column 2: ZZ500 -->
      <div class="flex-1 flex flex-col min-w-0">
        <div class="h-10 bg-gray-800/80 backdrop-blur border-b border-gray-700 flex items-center justify-center">
            <h2 class="font-bold text-gray-200">中证500 <span class="text-xs text-gray-500 font-normal">中盘成长</span></h2>
        </div>
        <div class="flex-1 overflow-y-auto p-2 scrollbar-hide">
            <StockCard v-for="item in lists.ZZ500" :key="item.id" :data="item" />
        </div>
      </div>

      <!-- Column 3: ZZ1000 -->
      <div class="flex-1 flex flex-col min-w-0">
        <div class="h-10 bg-gray-800/80 backdrop-blur border-b border-gray-700 flex items-center justify-center">
            <h2 class="font-bold text-gray-200">中证1000 <span class="text-xs text-gray-500 font-normal">中小活跃</span></h2>
        </div>
        <div class="flex-1 overflow-y-auto p-2 scrollbar-hide">
            <StockCard v-for="item in lists.ZZ1000" :key="item.id" :data="item" />
        </div>
      </div>

      <!-- Column 4: ZZ2000 -->
      <div class="flex-1 flex flex-col min-w-0">
        <div class="h-10 bg-gray-800/80 backdrop-blur border-b border-gray-700 flex items-center justify-center">
            <h2 class="font-bold text-gray-200">中证2000 <span class="text-xs text-gray-500 font-normal">微盘投机</span></h2>
        </div>
        <div class="flex-1 overflow-y-auto p-2 scrollbar-hide">
             <StockCard v-for="item in lists.ZZ2000" :key="item.id" :data="item" />
        </div>
      </div>

    </main>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted, onUnmounted } from 'vue';
import StockCard from './components/StockCard.vue';

// State
const lists = reactive({
    HS300: [],
    ZZ500: [],
    ZZ1000: [],
    ZZ2000: []
});

const isConnected = ref(false);
const totalAlerts = ref(0);
let socket = null;

// Helpers
const MAX_ITEMS_PER_COLUMN = 50;

const wsStatusText = computed(() => isConnected.value ? '已连接' : '已断开');
const wsStatusClass = computed(() => isConnected.value ? 'text-green-500' : 'text-red-500');

// WebSocket Logic
const connectWebSocket = () => {
    // Determine backend URL
    // Development: localhost:8000
    // Production: relative path or env var
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    
    // Check if we have an explicit backend URL in env, otherwise derive or default
    let wsHost = import.meta.env.VITE_BACKEND_HOST || 'localhost:8000';
    
    // If running on same domain in prod (e.g. via Nginx reverse proxy /api/ws)
    // We might need to adjust logic. 
    // For now, simple env var is best for docker flexibility.
    
    // If VITE_BACKEND_HOST is not set and we are in production, assume same host
    if (!import.meta.env.VITE_BACKEND_HOST && import.meta.env.PROD) {
        wsHost = window.location.host; // Use current window host
    }

    const wsUrl = `${protocol}//${wsHost}/ws/alerts`;
    console.log("Connecting WS to:", wsUrl);

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log("WebSocket connected");
        isConnected.value = true;
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleAlert(data);
        } catch (e) {
            console.error("Failed to parse message", e);
        }
    };

    socket.onclose = () => {
        console.log("WebSocket disconnected");
        isConnected.value = false;
        // Reconnect after 3s
        setTimeout(connectWebSocket, 3000);
    };
    
    socket.onerror = (err) => {
        console.error("WebSocket error", err);
    };
};

const handleAlert = (data) => {
    // Add unique ID for Vue :key
    data.id = new Date().getTime() + Math.random().toString(16).slice(2);
    
    const targetList = lists[data.index_code];
    if (targetList) {
        // Feature: Bubble Up (Remove existing instance of same stock so new one goes to top)
        const existingIdx = targetList.findIndex(item => item.code === data.code);
        if (existingIdx !== -1) {
            targetList.splice(existingIdx, 1);
        }

        // Unshift to add to top (Visual: Top is "Top of List")
        targetList.unshift(data);
        
        // Trim excess
        if (targetList.length > MAX_ITEMS_PER_COLUMN) {
            targetList.pop();
        }
        totalAlerts.value++;
    }
};

onMounted(() => {
    connectWebSocket();
});

onUnmounted(() => {
    if (socket) socket.close();
});
</script>

<style>
/* Custom Scrollbar hiding */
.scrollbar-hide::-webkit-scrollbar {
    display: none;
}
.scrollbar-hide {
    -ms-overflow-style: none;
    scrollbar-width: none;
}
</style>
