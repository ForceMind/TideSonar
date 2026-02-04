<template>
  <div 
    class="p-2 mb-2 rounded border-l-4 shadow-lg transition-all duration-300"
    :class="cardClass"
  >
    <div class="flex justify-between items-center mb-1">
      <div class="flex flex-col">
          <span class="font-bold text-lg tracking-wider">{{ data.name }}</span>
          <span class="text-xs text-gray-500 font-mono tracking-widest">{{ data.code }}</span>
      </div>
      <div class="flex flex-col text-right">
          <span class="text-xs px-2 py-0.5 rounded bg-blue-900/50 text-blue-200 border border-blue-800/50 mb-1">
            {{ data.industry || '未分类' }}
          </span>
          <span v-if="data.concept" class="text-[10px] text-gray-500 truncate max-w-[100px]">
            {{ data.concept }}
          </span>
      </div>
    </div>
    
    <div class="flex justify-between items-end">
      <div class="flex flex-col">
        <span class="text-xs text-gray-400">现价</span>
        <span class="font-mono text-base">{{ data.price.toFixed(2) }}</span>
      </div>
      
      <div class="flex flex-col items-end">
         <span class="font-bold text-lg" :class="textColorClass">
           {{ data.pct_chg > 0 ? '+' : '' }}{{ data.pct_chg.toFixed(2) }}%
         </span>
         <span class="text-xs text-gray-400">
            {{ formatAmount(data.amount) }}
         </span>
      </div>
    </div>
    
    <div class="mt-2 pt-1 border-t border-gray-700/50 flex justify-between text-xs">
        <span class="text-gray-500 font-mono scale-90 origin-left">{{ data.timestamp.split('T')[1].split('.')[0] }}</span>
        <span class="text-gray-300">量比: <span class="font-bold text-yellow-500">{{ data.volume_ratio }}</span></span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  data: {
    type: Object,
    required: true
  }
});

const isUp = computed(() => props.data.pct_chg > 0);

const cardClass = computed(() => {
  return isUp.value 
    ? 'bg-red-900/10 border-up-red hover:bg-red-900/20' 
    : 'bg-green-900/10 border-down-green hover:bg-green-900/20';
});

const textColorClass = computed(() => {
  return isUp.value ? 'text-up-red' : 'text-down-green';
});

function formatAmount(num) {
    if (num > 100000000) {
        return (num / 100000000).toFixed(1) + '亿';
    }
    return (num / 10000).toFixed(0) + '万';
}
</script>

<style scoped>
.animate-slide-in {
  animation: slideIn 0.3s ease-out forwards;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
