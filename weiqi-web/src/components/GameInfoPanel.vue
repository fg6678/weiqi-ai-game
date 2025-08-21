<template>
  <el-container class="game-info-section" direction="vertical">
    <el-header class="section-header">
      <el-icon class="header-icon"><InfoFilled /></el-icon>
      <span class="header-title">游戏信息</span>
    </el-header>
    <el-main>
    
    <!-- 胜率对比图 -->
    <div class="winrate-chart">
      <div class="unified-winrate-display">
        <div class="winrate-left">
          <span class="black-percent">{{ blackWinrate.toFixed(0) }}%</span>
        </div>
        <div class="unified-winrate-bar">
          <div class="black-winrate-fill" :style="{ width: blackWinrate + '%' }"></div>
        </div>
        <div class="winrate-right">
          <span class="white-percent">{{ whiteWinrate.toFixed(0) }}%</span>
        </div>
      </div>
    </div>

    <!-- 着法历史图表 -->
    <MoveHistoryChart
          ref="moveHistoryChart"
          :game-state="gameState"
          :ai-analysis="aiAnalysis"
          @go-to-move="$emit('go-to-move', $event)"
        />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed, ref } from 'vue'
import {
  InfoFilled
} from '@element-plus/icons-vue'
import MoveHistoryChart from './MoveHistoryChart.vue'

// Props
const props = defineProps({
  gameState: {
    type: Object,
    required: true
  },
  blackWinrate: {
    type: Number,
    required: true
  },
  whiteWinrate: {
    type: Number,
    required: true
  },
  aiAnalysis: {
    type: Array,
    default: () => []
  }
})

// 组件引用
const moveHistoryChart = ref(null)

// Emits
defineEmits(['go-to-move'])

// 计算最近的着法历史
const recentMoves = computed(() => {
  if (!props.gameState.moves || props.gameState.moves.length === 0) {
    return []
  }
  
  return props.gameState.moves.map((move, index) => {
    const [color, position] = move
    return {
      number: index + 1,
      color: color,
      position: position === 'pass' ? '跳过' : position
    }
  }).slice(-10) // 只显示最近10手
})

// 重置游戏信息面板
const resetGameInfo = () => {
  if (moveHistoryChart.value) {
    moveHistoryChart.value.resetChart()
  }
}

// 滚动到指定手数
const scrollToMove = (moveNumber) => {
  if (moveHistoryChart.value && moveHistoryChart.value.scrollToMove) {
    moveHistoryChart.value.scrollToMove(moveNumber)
  }
}

// 暴露方法给父组件
defineExpose({
  resetGameInfo,
  scrollToMove
})
</script>

<style scoped>
.game-info-section {
  margin-bottom: 0px;
  border: 1px solid #333;
  border-radius: 4px;
  background-color: #333;
  color: #333;
}

.section-header {
  display: flex;
  margin-top: -14px;
  align-items: center;
  gap: 3px;
}

.header-icon {
  color: #00ff88;
  scale: 1.3;
  margin-right: 6px;
}

.header-title {
  font-weight: 600;
  color: #00ff88;
}

:deep(.el-header) {
  padding: 8px;
  border-bottom: 1px solid #333;
  background-color: #2a2a2a;
}

:deep(.el-main) {
  padding: 8px;
  background-color: #2a2a2a;
  overflow-y: auto;
  /* 隐藏滚动条 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

:deep(.el-main)::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

/* 胜率图表样式 */
.winrate-chart {
  margin-bottom: 12px;
}

.unified-winrate-display {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}

.winrate-left, .winrate-right {
  min-width: 50px;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
}

.winrate-left {
  color: #ff6b35;
}

.winrate-right {
  color: #ddd;
}

.unified-winrate-bar {
  flex: 1;
  height: 20px;
  background: #ddd;
  border: 1px solid #666;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.black-winrate-fill {
  background: #333;
  height: 100%;
  transition: width 0.5s ease-in-out;
}

.black-percent {
  color: #00ff88;
}

.white-percent {
  color: #00ff88;
}

/* 着法历史 */
.move-history {
  margin-bottom: 8px;
}

.history-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.history-icon {
  color: #00ff88;
  scale: 1.1;
}

.history-title {
  font-size: 14px;
  color: #00ff88;
  font-weight: 600;
}

.move-count-text {
  font-size: 12px;
  color: #888;
  margin-left: auto;
}

.history-container {
  height: 200px;
  overflow-y: auto;
  /* 隐藏滚动条 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.history-container::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.history-list::-webkit-scrollbar {
  width: 0;
}

.history-list {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: #333;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.history-item:hover {
  background: #444;
  transform: translateX(2px);
}

.history-item.clickable {
  border-left: 3px solid transparent;
}

.history-item.clickable:hover {
  border-left-color: #00ff88;
}

.history-item .move-number {
  color: #888;
  min-width: 30px;
}

.history-item .move-color {
  font-size: 14px;
  min-width: 20px;
}

.history-item .move-position {
  color: #e0e0e0;
  font-weight: bold;
}
</style>