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
    <div v-if="showChart" class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4" @click.self="toggleChart">
      <!-- Modal Container -->
      <div class="bg-gray-900 border border-gray-700 rounded-lg shadow-2xl w-full md:w-3/4 lg:w-1/2 h-auto max-h-[90vh] flex flex-col overflow-hidden relative">
          
          <!-- Header (Fixed) -->
          <div class="flex justify-between items-center p-4 border-b border-gray-800 bg-gray-900 shrink-0">
              <h3 class="text-white font-bold">市场资金热度趋势</h3>
              <button @click="toggleChart" class="text-gray-400 hover:text-white text-xl leading-none">&times;</button>
          </div>
          
          <!-- Scrollable Body -->
          <div class="overflow-y-auto p-4 flex-1">
              <!-- Chart -->
              <div id="activity-chart" class="w-full h-64 mb-4 shrink-0"></div>
              
              <!-- Explanation Section -->
              <div class="p-4 bg-gray-800/50 rounded text-xs text-gray-400 space-y-2 border border-gray-700">
                  <p class="font-bold text-gray-300">🔥 什么是“热度”？</p>
                  <p>
                      热度值代表 <span class="text-blue-400">最近1分钟内新上榜的个股数量</span>。
                  </p>
                  
                  <p class="font-bold text-gray-300 mt-2">📊 数值解读：</p>
                  <ul class="list-disc list-inside space-y-1 ml-1">
                      <li><span class="text-green-400 font-mono">0 ~ 10</span> : <strong class="text-gray-300">情绪稳定</strong> — 龙头股锁仓惜售，排名稳固，适合持股待涨。</li>
                      <li><span class="text-yellow-400 font-mono">10 ~ 30</span>: <strong class="text-gray-300">正常轮动</strong> — 板块内部出现分歧，前排个股有买卖换手，注意观察承接力度。</li>
                      <li><span class="text-red-400 font-mono">> 30</span> : <strong class="text-gray-300">剧烈变盘</strong> — 大量新资金正在攻击新目标，老龙头被批量抛弃，市场处于高风险高收益的切换期。</li>
                  </ul>
              </div>
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
const currentChurnSet = reactive(new Set()); // Track unique stocks entering list per minute
const currentChurn = computed(() => currentChurnSet.size);

// Batch Processing Queue
const messageBuffer = [];
let batchProcessingTimer = null;
const BATCH_INTERVAL = 1000; // Process updates every 1 second (combines burst messages)

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
        title: { text: null }, // Remove Title to save space on mobile
        grid: { left: '15%', right: '5%', top: '10%', bottom: '20%', containLabel: true }, // Fix Mobile Cutoff
        tooltip: { trigger: 'axis', formatter: '{b} <br/> 热度: {c}' },
        legend: { data: ['今日', '昨日'], bottom: 0, textStyle: { color: '#ccc' } },
        xAxis: { 
            type: 'category', 
            data: todayTrend.map(i => i.time),
            axisLine: { lineStyle: { color: '#555' } },
            axisLabel: { color: '#888' }
        },
        yAxis: { 
            type: 'value', 
            splitLine: { lineStyle: { color: '#333' } },
            axisLine: { lineStyle: { color: '#555' } },
            axisLabel: { color: '#888' }
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
    currentChurnSet.clear();
    
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
            // DATA HEALING: If we detect huge numbers from previous version (>200), clear and restart
            const hasAnomaly = parsed.some(p => p.value > 200);
            if (hasAnomaly) {
                console.warn("Detected anomaly in history (old version data), clearing chart history.");
                localStorage.removeItem(key);
            } else {
                todayTrend.push(...parsed);
            }
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
        startBatchProcessor();
    };

    socket.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (Array.isArray(data)) {
                 messageBuffer.push(...data);
            } else {
                 messageBuffer.push(data);
            }
        } catch (e) {
            console.error("Failed to parse message", e);
        }
    };

    socket.onclose = () => {
        console.log("WebSocket disconnected");
        isConnected.value = false;
        stopBatchProcessor();
        // Reconnect after 3s
        setTimeout(connectWebSocket, 3000);
    };
    
    socket.onerror = (err) => {
        console.error("WebSocket error", err);
    };
};


// Batch Processor: Runs every X ms to apply updates efficiently
const startBatchProcessor = () => {
    if (batchProcessingTimer) clearInterval(batchProcessingTimer);
    
    batchProcessingTimer = setInterval(() => {
        if (messageBuffer.length === 0) return;
        
        // Take all items from buffer
        const batch = messageBuffer.splice(0, messageBuffer.length);
        processBatch(batch);
        
    }, BATCH_INTERVAL);
};

const stopBatchProcessor = () => {
    if (batchProcessingTimer) clearInterval(batchProcessingTimer);
};

const processBatch = (batchItems) => {
    // Group updates by index to avoid re-sorting multiple times for the same list
    const updatesByIndex = {
        HS300: [],
        ZZ500: [],
        ZZ1000: [],
        ZZ2000: []
    };
    
    // 1. Distribute updates
    batchItems.forEach(data => {
        data.id = data.code; // Ensure ID for Vue key
        if (updatesByIndex[data.index_code]) {
            updatesByIndex[data.index_code].push(data);
        }
    });
    
    // 2. Process each list ONCE
    Object.keys(updatesByIndex).forEach(indexCode => {
        const indexUpdates = updatesByIndex[indexCode];
        if (indexUpdates.length === 0) return;
        
        const targetList = lists[indexCode];
        if (!targetList) return;
        
        indexUpdates.forEach(data => {
            const existingIdx = targetList.findIndex(item => String(item.code) === String(data.code));
            
            if (existingIdx !== -1) {
                // Update in place
                targetList[existingIdx] = data;
            } else {
                // Add new
                // Check Churn logic
                if (targetList.length >= MAX_ITEMS_PER_COLUMN) {
                    currentChurnSet.add(data.code);
                }
                targetList.push(data);
            }
        });
        
        // 3. Sort ONCE after batch applies
        targetList.sort((a, b) => b.amount - a.amount);
        
        // 4. Trim ONCE after sort
        if (targetList.length > MAX_ITEMS_PER_COLUMN) {
             targetList.splice(MAX_ITEMS_PER_COLUMN);
        }
    });
};

onMounted(() => {
    connectWebSocket();
    startBatchProcessor();
});

onUnmounted(() => {
    if (socket) socket.close();
    stopBatchProcessor();
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
