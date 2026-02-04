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

    <!-- Main Content: 4 Columns (Mobile: Stacked 4 Rows, Desktop: 4 Columns) -->
    <main class="flex-1 flex flex-col md:flex-row overflow-hidden md:divide-x divide-y md:divide-y-0 divide-gray-700">
      
      <!-- Column 1: HS300 -->
      <div class="flex-1 flex flex-col min-w-0 min-h-0">
        <div class="h-10 bg-gray-800/80 backdrop-blur border-b border-gray-700 flex items-center justify-center shrink-0">
            <h2 class="font-bold text-gray-200">沪深300 <span class="text-xs text-gray-500 font-normal">核心资产</span></h2>
        </div>
        <div class="flex-1 overflow-y-auto p-2 scrollbar-hide">
            <TransitionGroup name="list" tag="div" class="relative">
                <StockCard v-for="item in lists.HS300" :key="item.id" :data="item" />
            </TransitionGroup>
        </div>
      </div>

      <!-- Column 2: ZZ500 -->
      <div class="flex-1 flex flex-col min-w-0 min-h-0">
        <div class="h-10 bg-gray-800/80 backdrop-blur border-b border-gray-700 flex items-center justify-center shrink-0">
            <h2 class="font-bold text-gray-200">中证500 <span class="text-xs text-gray-500 font-normal">中盘成长</span></h2>
        </div>
        <div class="flex-1 overflow-y-auto p-2 scrollbar-hide">
            <TransitionGroup name="list" tag="div" class="relative">
                <StockCard v-for="item in lists.ZZ500" :key="item.id" :data="item" />
            </TransitionGroup>
        </div>
      </div>

      <!-- Column 3: ZZ1000 -->
      <div class="flex-1 flex flex-col min-w-0 min-h-0">
        <div class="h-10 bg-gray-800/80 backdrop-blur border-b border-gray-700 flex items-center justify-center shrink-0">
            <h2 class="font-bold text-gray-200">中证1000 <span class="text-xs text-gray-500 font-normal">中小活跃</span></h2>
        </div>
        <div class="flex-1 overflow-y-auto p-2 scrollbar-hide">
            <TransitionGroup name="list" tag="div" class="relative">
                <StockCard v-for="item in lists.ZZ1000" :key="item.id" :data="item" />
            </TransitionGroup>
        </div>
      </div>

      <!-- Column 4: ZZ2000 -->
      <div class="flex-1 flex flex-col min-w-0 min-h-0">
        <div class="h-10 bg-gray-800/80 backdrop-blur border-b border-gray-700 flex items-center justify-center shrink-0">
            <h2 class="font-bold text-gray-200">中证2000 <span class="text-xs text-gray-500 font-normal">微盘投机</span></h2>
        </div>
        <div class="flex-1 overflow-y-auto p-2 scrollbar-hide">
             <TransitionGroup name="list" tag="div" class="relative">
                 <StockCard v-for="item in lists.ZZ2000" :key="item.id" :data="item" />
             </TransitionGroup>
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
    // and let Nginx Proxy handle the port mapping (Standard Docker/Server Setup)
    if (!import.meta.env.VITE_BACKEND_HOST && import.meta.env.PROD) {
        // Nginx is on same host, proxies /ws/ to backend
        // So we connect to wss://hostname/ws/alerts
        wsHost = window.location.host; 
    }

    // Handle Proxy Path: If using Nginx proxy, wsUrl should probably be just host + path
    // If wsHost includes port (dev), logic is fine.
    // If wsHost is plain domain (prod), logic is fine.
    
    // Fix: If running behind Nginx with /ws/ location, we don't need port 8000
    // The previous logic defaulted to 'localhost:8000'.
    // New logic: Use relative path for WebSocket if supported, or absolute from window.location
    
    let wsUrl_final = '';
    
    if (import.meta.env.PROD) {
       // Production: Use relative protocol and host, Nginx handles /ws route
       // window.location.host includes the port if custom (e.g. 8080)
       wsUrl_final = `${protocol}//${window.location.host}/ws/alerts`;
    } else {
       // Dev: Explicit Backend Port
       wsUrl_final = `ws://localhost:8000/ws/alerts`;
    }

    console.log("Connecting WS to:", wsUrl_final);

    socket = new WebSocket(wsUrl_final);

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
    // Add unique ID for Vue :key (Use Code for Persistence + Animation)
    data.id = data.code;
    
    const targetList = lists[data.index_code];
    if (targetList) {
        // Feature: Ranking Board (Sort by Amount)
        // 1. Check if exists
        const existingIdx = targetList.findIndex(item => item.code === data.code);
        
        if (existingIdx !== -1) {
            // Update usage
            targetList[existingIdx] = data;
        } else {
            // Add new
            targetList.push(data);
        }

        // 2. Sort by Amount (Descending) to maintain consistent ranking
        targetList.sort((a, b) => b.amount - a.amount);
        
        // 3. Trim excess (Keep Top X)
        if (targetList.length > MAX_ITEMS_PER_COLUMN) {
             targetList.splice(MAX_ITEMS_PER_COLUMN);
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

/* List Transitions */
.list-move,
.list-enter-active,
.list-leave-active {
  transition: all 0.5s cubic-bezier(0.55, 0, 0.1, 1);
}

.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

.list-leave-active {
  position: absolute;
  width: 100%;
}
</style>
