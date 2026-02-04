<template>
  <div class="h-screen w-screen flex flex-col bg-gray-900 overflow-hidden font-sans">
    <!-- Header -->
    <header class="h-12 bg-gray-800 border-b border-gray-700 flex items-center px-4 justify-between select-none">
      <div class="flex items-center space-x-2">
        <div class="w-3 h-3 rounded-full bg-blue-500 animate-pulse"></div>
        <h1 class="text-xl font-bold tracking-tight text-white">观潮 <span class="text-blue-500 font-light">TideSonar</span></h1>
      </div>
      <div class="flex items-center space-x-2">
          <!-- Mobile: Hide label, just show dot -->
          <span class="flex items-center text-xs uppercase tracking-widest text-gray-500" :class="wsStatusClass">
              <span class="hidden md:inline">● {{ wsStatusText }}</span>
              <span class="md:hidden">●</span>
          </span>
          
          <button @click="toggleChart" class="bg-gray-800 hover:bg-gray-700 text-gray-300 px-2 md:px-3 py-1 rounded text-sm font-mono transition-colors border border-gray-700 whitespace-nowrap">
              <span class="hidden md:inline">⚡ 热度: {{ currentChurn }}/min</span>
              <span class="md:hidden">⚡ {{ currentChurn }}</span>
          </button>
      </div>
    </header>

    <!-- Chart Modal -->
    <div v-if="showChart" class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm" @click.self="toggleChart">
      <div class="bg-gray-900 border border-gray-700 p-4 rounded-lg shadow-2xl w-11/12 md:w-3/4 lg:w-1/2 h-1/2 flex flex-col">
          <div class="flex justify-between items-center mb-2">
              <h3 class="text-white font-bold">市场资金热度趋势</h3>
              <button @click="toggleChart" class="text-gray-400 hover:text-white text-xl leading-none">&times;</button>
          </div>
          <div id="activity-chart" class="flex-1 w-full h-full"></div>
          <div class="text-xs text-gray-500 mt-2 text-center">
              * 统计每一分钟内新进入Top30榜单的个股数量，反映市场资金的轮动速度。
          </div>
      </div>
    </div>

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
import { reactive, ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import StockCard from './components/StockCard.vue';
import * as echarts from 'echarts';

// State
const lists = reactive({
    HS300: [],
    ZZ500: [],
    ZZ1000: [],
    ZZ2000: []
});

const isConnected = ref(false);
const currentChurn = ref(0); // Real-time new entry counter (Current Minute)
const showChart = ref(false);
let chartInstance = null;

// History Data for Chart
const todayTrend = reactive([]); 

let socket = null;

// Helpers
const MAX_ITEMS_PER_COLUMN = 30; // Strict Top 30

const wsStatusText = computed(() => isConnected.value ? '已连接' : '已断开');
const wsStatusClass = computed(() => isConnected.value ? 'text-green-500' : 'text-red-500');

// Chart Logic
const toggleChart = async () => {
    showChart.value = !showChart.value;
    if (showChart.value) {
        await nextTick();
        initChart();
    }
};

const initChart = () => {
    const el = document.getElementById('activity-chart');
    if (!el) return;
    
    // Dispose old if exists
    if (chartInstance) chartInstance.dispose();
    
    chartInstance = echarts.init(el, 'dark');
    
    // Mock History (Yesterday) - usually from LocalStorage
    // For demo, we generate a random "Yesterday" based on "Today" shape or flat
    const yesterdayData = generateMockHistory(); 
    
    const option = {
        backgroundColor: 'transparent',
        title: { text: '市场热度趋势 (新上榜数量/分)', left: 'center', textStyle: { color: '#ddd' } },
        tooltip: { trigger: 'axis' },
        legend: { data: ['今日', '昨日'], bottom: 0, textStyle: { color: '#ccc' } },
        xAxis: { 
            type: 'category', 
            data: todayTrend.map(i => i.time),
            axisLine: { lineStyle: { color: '#555' } }
        },
        yAxis: { 
            type: 'value', 
            splitLine: { lineStyle: { color: '#333' } },
             axisLine: { lineStyle: { color: '#555' } }
        },
        series: [
            {
                name: '今日',
                type: 'line',
                data: todayTrend.map(i => i.value),
                smooth: true,
                showSymbol: false,
                itemStyle: { color: '#ef4444' }, // Red
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                      { offset: 0, color: 'rgba(239,68,68,0.5)' },
                      { offset: 1, color: 'rgba(239,68,68,0.0)' }
                    ])
                }
            },
            {
                name: '昨日',
                type: 'line',
                data: yesterdayData, 
                smooth: true,
                showSymbol: false,
                lineStyle: { type: 'dashed' },
                itemStyle: { color: '#6b7280' } // Gray
            }
        ]
    };
    chartInstance.setOption(option);
};

// Generate mock yesterday data matching current length or full day
const generateMockHistory = () => {
    // Just random noise around 10-50
    const len = Math.max(todayTrend.length, 60); 
    return Array.from({length: len}, () => Math.floor(Math.random() * 40) + 10);
};

// Timer for Trend
setInterval(() => {
    const now = new Date();
    const timeStr = now.toTimeString().slice(0, 5); // HH:MM
    
    // Push current minute's churn
    todayTrend.push({
        time: timeStr,
        value: currentChurn.value
    });
    
    // Persist to LocalStorage (Simple Today Key)
    const key = `tide_trend_${now.toISOString().slice(0,10)}`;
    localStorage.setItem(key, JSON.stringify(todayTrend));
    
    // Reset counter for next minute
    currentChurn.value = 0;
    
    // Update chart if open
    if (showChart.value && chartInstance) {
        chartInstance.setOption({
            xAxis: { data: todayTrend.map(i => i.time) },
            series: [
                { data: todayTrend.map(i => i.value) },
                { data: generateMockHistory() } // Keep sync
            ]
        });
    }
}, 60000); // Every minute

// Restore on Load
const restoreHistory = () => {
    const now = new Date();
    const key = `tide_trend_${now.toISOString().slice(0,10)}`;
    const saved = localStorage.getItem(key);
    if (saved) {
        try {
            const parsed = JSON.parse(saved);
            todayTrend.push(...parsed);
        } catch(e) {}
    }
};

restoreHistory();

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
        const existingIdx = targetList.findIndex(item => String(item.code) === String(data.code));
        
        if (existingIdx !== -1) {
            // Update usage
            targetList[existingIdx] = data;
        } else {
            // Add new (This is a CHURN event)
            // Only count as Churn if the list was already full (meaning we are displacing someone)
            // This prevents the initial page load (0 -> 120 items) from counting as "High Churn"
            if (targetList.length >= MAX_ITEMS_PER_COLUMN) {
                currentChurn.value++;
            }
            targetList.push(data);
        }

        // 2. Sort by Amount (Descending) to maintain consistent ranking
        targetList.sort((a, b) => b.amount - a.amount);
        
        // 3. Trim excess (Keep Top X)
        if (targetList.length > MAX_ITEMS_PER_COLUMN) {
             targetList.splice(MAX_ITEMS_PER_COLUMN);
        }
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
