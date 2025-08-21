<template>
  <el-container class="story-section" direction="vertical">
    <el-header class="section-header">
      <el-icon class="header-icon"><Document /></el-icon>
      <span class="header-title">对局故事线</span>
      <div class="model-info">
        <span class="model-name">实时记录</span>
      </div>
    </el-header>
    <el-main>
      <!-- 故事时间线 -->
      <div class="story-history" ref="storyHistory">
        <div 
          v-for="(event, index) in storyEvents" 
          :key="index" 
          class="story-item"
        >
          <div class="story-avatar">
            <el-icon class="timeline-icon"><Clock /></el-icon>
          </div>
          <div class="story-content">
            <div class="story-text">{{ event.description }}</div>
            <div class="story-time">{{ event.time }}</div>
          </div>
        </div>
      </div>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Document, Clock } from '@element-plus/icons-vue'

const props = defineProps({
  gameState: {
    type: Object,
    required: true
  }
})

// 故事事件数据
const storyEvents = computed(() => {
  const events = []
  
  // 游戏开始事件
  events.push({
    time: '开局',
    description: '对局开始，黑先白后'
  })
  
  // 根据棋局状态生成故事事件
  if (props.gameState.moves && props.gameState.moves.length > 0) {
    const moves = props.gameState.moves
    
    // 开局阶段
    if (moves.length <= 10) {
      events.push({
        time: `第${moves.length}手`,
        description: '双方进入布局阶段，争夺角部要点'
      })
    }
    // 中盘阶段
    else if (moves.length <= 100) {
      events.push({
        time: `第${moves.length}手`,
        description: '进入中盘战斗，双方展开激烈争夺'
      })
    }
    // 官子阶段
    else {
      events.push({
        time: `第${moves.length}手`,
        description: '进入官子阶段，细算每一目棋'
      })
    }
  }
  
  // 游戏结束事件
  if (props.gameState.game_over) {
    events.push({
      time: '终局',
      description: '对局结束，感谢对弈'
    })
  }
  
  return events
})
</script>

<style scoped>
.story-section {
  padding-top: 10px;
  padding-bottom: 10px;
  padding-left: 8px;
  padding-right: 8px;
  margin-bottom: 0px;
  border: 1px solid #444;
  border-radius: 8px;
  background-color: #2a2a2a;
  color: #333;
  height: 100%;
  margin-top: 0px;
}

.section-header {
  display: flex;
  margin-top: -8px;
  align-items: center;
  gap: 3px;
  justify-content: space-between;
}

.header-icon {
  color: #00ff88;
  scale: 1.3;
  margin-right: 6px;
}

.header-title {
  font-weight: 600;
  color: #00ff88;
  flex: 1;
}

.model-info {
  display: flex;
  align-items: center;
}

.model-name {
  color: #888;
  font-size: 12px;
  background: #444;
  padding: 4px 8px;
  border-radius: 4px;
}

:deep(.el-header) {
  padding: 12px;
  border-bottom: 1px solid #444;
  background-color: #2a2a2a;
}

:deep(.el-main) {
  padding: 0;
  background-color: #2a2a2a;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  /* 隐藏滚动条 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

:deep(.el-main)::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.story-history {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  /* 隐藏滚动条 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.story-history::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.story-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.story-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: rgba(0, 255, 136, 0.1);
}

.timeline-icon {
  color: #00ff88;
  font-size: 16px;
}

.story-content {
  flex: 1;
  max-width: calc(100% - 44px);
}

.story-text {
  background: #333;
  padding: 8px 12px;
  border-radius: 8px;
  color: #e0e0e0;
  font-size: 14px;
  line-height: 1.4;
  margin-bottom: 4px;
}

.story-time {
  font-size: 12px;
  color: #888;
  padding-left: 4px;
}
</style>