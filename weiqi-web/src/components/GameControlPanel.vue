<template>
  <el-container class="control-section" direction="vertical">
    <el-header class="section-header">
      <el-icon class="header-icon"><Monitor /></el-icon>
      <span class="header-title">游戏控制</span>
    </el-header>
    <el-main>
    
    <!-- 游戏状态显示 -->
    <div class="status-display">

      <div class="game-status" v-if="gameState.game_over">
        <el-alert
          title="游戏结束"
          type="warning"
          :closable="false"
          show-icon
        />
      </div>
      <div class="ai-status" v-if="aiThinking">
        <el-alert
          title="🤔 KataGo 思考中..."
          type="info"
          :closable="false"
          show-icon
        />
      </div>
    </div>

    <!-- 控制按钮组 -->
    <div class="control-buttons">
      <el-row :gutter="12" justify="center">
        <el-col :span="6">
          <el-button 
            @click="$emit('toggle-game-session')" 
            :type="gameSessionActive ? 'danger' : 'success'"
            size="middle"
          >
            <el-icon class="b-icons"><VideoPause v-if="gameSessionActive" /><VideoPlay v-else /></el-icon>
          </el-button>
        </el-col>
        <el-col :span="6">
          <el-button 
            @click="$emit('new-game')" 
            type="primary"
            size="middle"
            :disabled="!gameSessionActive"
          >
            <el-icon class="b-icons"><Plus /></el-icon>
          </el-button>
        </el-col>
        <el-col :span="6">
          <el-button 
            @click="$emit('undo-move')" 
            type="warning"
            size="middle"
            :disabled="!gameSessionActive || gameState.move_count === 0 || gameState.game_over || aiThinking"
          >
            <el-icon class="b-icons"><RefreshLeft /></el-icon>
          </el-button>
        </el-col>
        <el-col :span="6">
          <el-button 
            @click="$emit('pass')" 
            type="info"
            size="middle"
            :disabled="!gameSessionActive || gameState.game_over || (gameMode === 'human_vs_ai' && (gameState.current_player !== gameSettings.playerColor || aiThinking)) || (gameMode === 'analysis' && aiThinking)"
          >
            <el-icon class="b-icons"><Right /></el-icon>
          </el-button>
        </el-col>
      </el-row>
      

      
      <!-- 点目功能按钮行 -->
      <el-row :gutter="12" justify="center" style="margin-top: 8px;">
        <el-col :span="12">
          <el-button 
            @click="$emit('calculate-territory')" 
            type="success"
            size="small"
            :disabled="!gameSessionActive || aiThinking"
            style="width: 86%;"
          >
            终局点目
          </el-button>
        </el-col>
        <el-col :span="12">
          <el-button 
            @click="$emit('territory-preview')" 
            type="default"
            size="small"
            :disabled="aiThinking"
            style="width: 86%;"
          >
            {{ territoryPreviewActive ? '关闭预览' : '领地预览' }}
          </el-button>
        </el-col>
      </el-row>
      

    </div>

    <el-form class="game-settings" label-position="top">
      <!-- 玩家颜色选择 - 仅在Human vs AI模式显示 -->
      <el-form-item v-if="gameMode === 'human_vs_ai'" label="玩家执子">
        <select 
          v-model="gameSettings.playerColor" 
          @change="$emit('player-color-change')"
          class="custom-select"
        >
          <option value="B">黑棋</option>
          <option value="W">白棋</option>
        </select>
      </el-form-item>

      <!-- AI算力设置 -->
      <el-form-item :label="gameMode === 'human_vs_ai' ? '对手AI算力' : 'AI算力'">
        <select 
          v-model="gameSettings.aiStrength" 
          @change="$emit('ai-strength-change')"
          class="custom-select"
        >
          <option value="1">弱 (1秒)</option>
          <option value="3">中 (3秒)</option>
          <option value="5">强 (5秒)</option>
          <option value="10">极强 (10秒)</option>
        </select>
      </el-form-item>

      <!-- 贴目设置 -->
      <el-form-item :label="`贴目: ${gameSettings.komi}目`">
        <el-slider
          v-model="gameSettings.komi"
          :min="0"
          :max="10"
          :step="0.5"
          @input="$emit('komi-change')"
          style="width: 100%"
        />
      </el-form-item>

      <!-- 规则设置 -->
      <el-form-item label="规则">
        <select 
          v-model="gameSettings.rules" 
          @change="$emit('rules-change')"
          class="custom-select"
        >
          <option value="chinese">中国规则</option>
          <option value="japanese">日本规则</option>
          <option value="korean">韩国规则</option>
        </select>
      </el-form-item>

      <!-- SGF文件导入 - 仅在推演模式显示 -->
      <el-form-item v-if="gameMode === 'analysis'" label="SGF文件">
        <div class="sgf-upload-wrapper">
          <input 
            ref="sgfFileInput"
            type="file" 
            accept=".sgf"
            @change="handleSgfFileSelect"
            style="display: none;"
          />
          <div 
            class="custom-select sgf-upload-select" 
            :class="{ 'disabled': aiThinking }"
            @click="triggerFileSelect"
            @mousedown.prevent
          >
            {{ selectedFileName || '点击选择SGF文件' }}
          </div>
        </div>
      </el-form-item>
    </el-form>


    <el-form class="ai-suggestions-control" label-position="top">
      <el-form-item label="AI选点">
        <select 
          v-model="suggestionSettings.count" 
          @change="$emit('suggestion-count-change')"
          class="custom-select"
        >
          <option value="0">隐藏</option>
          <option value="3">3个</option>
          <option value="5">5个</option>
          <option value="7">7个</option>
        </select>
      </el-form-item>
    </el-form>
    </el-main>
  </el-container>
</template>

<script setup>
import {
  Monitor,
  VideoPause,
  VideoPlay,
  Plus,
  RefreshLeft,
  Right,
  Upload
} from '@element-plus/icons-vue'
import { ref } from 'vue'

// Props
defineProps({
  gameState: {
    type: Object,
    required: true
  },
  gameSettings: {
    type: Object,
    required: true
  },
  suggestionSettings: {
    type: Object,
    required: true
  },
  gameSessionActive: {
    type: Boolean,
    required: true
  },
  aiThinking: {
    type: Boolean,
    required: true
  },
  territoryPreviewActive: {
    type: Boolean,
    required: true
  },
  gameMode: {
    type: String,
    required: true
  },

})

// Emits
const emit = defineEmits([
  'toggle-game-session',
  'new-game',
  'undo-move',
  'pass',
  'player-color-change',
  'ai-strength-change',
  'suggestion-ai-strength-change',
  'komi-change',
  'rules-change',
  'suggestion-count-change',
  'calculate-territory',
  'territory-preview',
  'import-sgf'
])

// 响应式数据
const sgfFileInput = ref(null)
const selectedFileName = ref('')

// 触发文件选择
const triggerFileSelect = () => {
  console.log('triggerFileSelect called', sgfFileInput.value)
  if (sgfFileInput.value) {
    sgfFileInput.value.click()
    console.log('File input clicked')
  } else {
    console.error('sgfFileInput ref is null')
  }
}

// SGF文件选择处理
const handleSgfFileSelect = (event) => {
  const file = event.target.files[0]
  if (file) {
    selectedFileName.value = file.name
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const sgfContent = e.target.result
        emit('import-sgf', sgfContent)
      } catch (error) {
        console.error('读取SGF文件失败:', error)
        selectedFileName.value = ''
        // 这里可以添加错误提示
      }
    }
    reader.readAsText(file)
  }
}
</script>

<style scoped>
/* Element Plus 组件的自定义样式 */
.section-header {
  display: flex;
  margin-top: -8px;
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

.status-display {
  margin-bottom: 8px;
}

.control-buttons {
  margin-bottom: 12px;
  margin-left: 15px;
  margin-top: -5px;
}

.game-settings {
  margin-bottom: 12px;
}

.ai-suggestions-control {
  margin-bottom: 12px;
}

/* 自定义 Element Plus 组件样式 */
:deep(.el-slider__runway) {
  background-color: #333;
}

:deep(.el-slider__bar) {
  background-color: #00ff88;
}

:deep(.el-slider__button) {
  border-color: #00ff88;
  background-color: #00ff88;
}

:deep(.el-slider__button:hover) {
  border-color: #00cc66;
  background-color: #00cc66;
}

:deep(.el-slider__marks-text) {
  color: #00ff88;
}

:deep(.el-divider__text) {
  color: #00ff88;
}

:deep(.el-divider) {
  border-color: #00ff88;
}

/* SGF上传样式 */
.sgf-upload-wrapper {
  width: 100%;
}

.sgf-upload-select {
  cursor: pointer;
  pointer-events: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: relative;
}

.sgf-upload-select::after {
  content: '';
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 6px solid #888;
  margin-left: 8px;
}

.sgf-upload-select:hover {
  background-color: #2a2a2a;
  border-color: #666;
}

.sgf-upload-select.disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background-color: #1a1a1a;
  pointer-events: none;
}

.sgf-upload-select.disabled::after {
  border-top-color: #555;
}

.control-section {
  margin-bottom: 0px;
  border: 1px solid #333;
  border-radius: 4px;
  background-color: #333;
  color: #333;
}

:deep(.el-header) {
  padding: 12px;
  border-bottom: 1px solid #333;
  background-color: #2a2a2a;
}

:deep(.el-main) {
  padding: 12px;
  background-color: #2a2a2a;
  overflow-y: auto;
  /* 隐藏滚动条 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

:deep(.el-main)::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

/* 表单项水平布局 */
:deep(.el-form-item) {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

:deep(.el-form-item__label) {
  width: 120px;
  margin-right: 12px;
  margin-bottom: 0;
  color: #00ff88;
  flex-shrink: 0;
}

:deep(.el-form-item__content) {
  flex: 1;
  margin-left: 0;
}

/* ================================ 
   Custom Select - Dark Neon Theme
   主题色：#00ff88 / 深灰背景：#1a1a1a
   ================================ */ 

.custom-select {
  width: 100%;
  padding: 8px 12px;
  background: #2a2a2a;
  border: 1px solid #444;
  border-radius: 4px;
  color: #ccc;
  font-size: 14px;
  outline: none;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
}

.custom-select:hover {
  background: #333;
  border-color: #555;
}

.custom-select:focus {
  background: #333;
  border-color: #666;
}

.custom-select option {
  background: #2a2a2a;
  color: #ccc;
  padding: 8px;
}

.custom-select option:checked {
  background: #444;
  color: #fff;
}

.custom-select option:hover {
  background: #333;
  color: #fff;
}
.b-icons{
  scale: 1.3;
}


/* 按钮保持原来的颜色 */

:deep(.el-tag) {
  background-color: #2a2a2a;
  border-color: #333;
  color: #fff;
}

:deep(.el-alert) {
  background-color: #2a2a2a;
  border-color: #333;
  color: #fff;
}

/* 响应式布局 */
@media (max-width: 768px) {
  .control-buttons {
    flex-direction: column;
  }
}
</style>