<template>
  <el-container class="ai-commentary-section" direction="vertical">
    <el-header class="section-header">
      <el-icon class="header-icon"><ChatDotRound /></el-icon>
      <span class="header-title">AI讲棋</span>
      <div class="model-info">
        <el-select 
          v-model="selectedModel" 
          @change="handleModelChange"
          class="model-select"
          size="small"
          placeholder="选择模型"
          :loading="modelsLoading"
          loading-text="加载模型中..."
        >
          <el-option
            v-for="model in availableModels"
            :key="model.value"
            :label="model.label"
            :value="model.value"
          />
        </el-select>
      </div>
    </el-header>
    <el-main>
      <!-- 对话历史 -->
      <div class="chat-history" ref="chatHistory">
        <div 
          v-for="(message, index) in chatMessages" 
          :key="index" 
          :class="['message', message.type]"
        >
          <div class="message-avatar">
            <img v-if="message.type === 'ai'" src="@/assets/ai-avatar.svg" class="ai-avatar-img" alt="AI头像" />
            <el-icon v-else class="user-avatar"><User /></el-icon>
          </div>
          <div class="message-content">
            <div class="message-text">{{ message.content }}</div>
            <div class="message-time">{{ formatTime(message.timestamp) }}</div>
          </div>
        </div>
        
        <!-- AI思考中状态 -->
        <div v-if="aiThinking" class="message ai thinking">
          <div class="message-avatar">
            <img src="@/assets/ai-avatar.svg" class="ai-avatar-img thinking-icon" alt="AI头像" />
          </div>
          <div class="message-content">
            <div class="thinking-dots">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 输入区域 -->
      <div class="chat-input-area">
        <div class="input-container">
          <el-input
            v-model="userInput"
            type="textarea"
            :rows="2"
            placeholder="向AI提问关于当前局面的问题..."
            @keydown.enter.prevent="handleSendMessage"
            :disabled="aiThinking"
            resize="none"
          />
          <el-button 
            @click="handleSendMessage" 
            type="primary" 
            :disabled="!userInput.trim() || aiThinking"
            class="send-button"
            text
          >
            <el-icon class="b-icons"><Promotion /></el-icon>
          </el-button>
        </div>
      </div>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { 
  ChatDotRound, 
  User, 
  Promotion 
} from '@element-plus/icons-vue'

const props = defineProps({
  gameState: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['send-message'])

// 响应式数据
const chatMessages = ref([
  {
    type: 'ai',
    content: '欢迎来到AI讲棋！我是您的围棋助手，可以为您分析局面、解释着法，也可以回答您的围棋问题。',
    timestamp: Date.now()
  }
])

const userInput = ref('')
const aiThinking = ref(false)
const chatHistory = ref(null)

// 模型选择相关
const selectedModel = ref('qwen3:4b-instruct')
const availableModels = ref([])
const modelsLoading = ref(false)

// 移除了实时更新逻辑，改为纯一问一答模式

// 处理用户发送消息
function handleSendMessage() {
  if (!userInput.value.trim() || aiThinking.value) return
  
  // 添加用户消息
  chatMessages.value.push({
    type: 'user',
    content: userInput.value.trim(),
    timestamp: Date.now()
  })
  
  // 发送到后端
  emit('send-message', {
    type: 'user_question',
    message: userInput.value.trim(),
    gameState: props.gameState
  })
  
  userInput.value = ''
  aiThinking.value = true
  
  scrollToBottom()
}

// 获取可用模型列表
const fetchAvailableModels = async () => {
  try {
    modelsLoading.value = true
    const response = await fetch('http://localhost:8000/api/models')
    const data = await response.json()
    
    if (data.models && data.models.length > 0) {
      availableModels.value = data.models
      // 如果当前选中的模型不在列表中，选择第一个可用模型
      if (!data.models.find(m => m.value === selectedModel.value)) {
        selectedModel.value = data.models[0].value
      }
    } else {
      // 使用默认模型列表
       availableModels.value = [
         { label: 'qwen3:4b-instruct', value: 'qwen3:4b-instruct' },
         { label: 'qwen3:30b-instruct', value: 'qwen3:30b-instruct' }
       ]
    }
  } catch (error) {
    console.error('获取模型列表失败:', error)
    // 使用默认模型列表
     availableModels.value = [
       { label: 'qwen3:4b-instruct', value: 'qwen3:4b-instruct' },
       { label: 'qwen3:30b-instruct', value: 'qwen3:30b-instruct' }
     ]
  } finally {
    modelsLoading.value = false
  }
}

// 处理模型切换
function handleModelChange(newModel) {
  console.log('切换AI模型:', newModel)
  // 发送模型切换事件到后端
  emit('send-message', {
    type: 'change_model',
    model: newModel,
    gameState: props.gameState
  })
  
  // 添加系统消息提示模型已切换
  chatMessages.value.push({
    type: 'ai',
    content: `已切换到 ${availableModels.value.find(m => m.value === newModel)?.label} 模型`,
    timestamp: Date.now()
  })
  
  scrollToBottom()
}

// 接收AI回复
function receiveAIMessage(content) {
  aiThinking.value = false
  
  chatMessages.value.push({
    type: 'ai',
    content: content,
    timestamp: Date.now()
  })
  
  scrollToBottom()
}

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (chatHistory.value) {
      chatHistory.value.scrollTop = chatHistory.value.scrollHeight
    }
  })
}

// 格式化时间
function formatTime(timestamp) {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

// 重置聊天记录
function resetChatMessages() {
  chatMessages.value = [
    {
      type: 'ai',
      content: '欢迎来到AI讲棋！我是您的围棋助手，可以为您分析局面、解释着法，也可以回答您的围棋问题。',
      timestamp: Date.now()
    }
  ]
  aiThinking.value = false
  userInput.value = ''
}

// 组件挂载时初始化
onMounted(() => {
  fetchAvailableModels()
})

// 暴露方法给父组件
defineExpose({
  receiveAIMessage,
  resetChatMessages,
  selectedModel,
  availableModels,
  handleModelChange,
  fetchAvailableModels
})
</script>

<style scoped>
.ai-commentary-section {
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

.model-select {
  width: 140px;
}

.model-select :deep(.el-input__wrapper) {
  background-color: #666;
  border: 1px solid #888;
  border-radius: 4px;
  box-shadow: none;
}

.model-select :deep(.el-input__wrapper:hover) {
  border-color: #aaa;
  background-color: #777;
}

.model-select :deep(.el-input__wrapper.is-focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
  background-color: #777;
}

.model-select :deep(.el-input__inner) {
  color: #fff;
  font-size: 12px;
  background: transparent;
}

.model-select :deep(.el-input__suffix) {
  color: rgba(255, 255, 255, 0.8);
}

.model-select :deep(.el-input__suffix:hover) {
  color: #fff;
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

.chat-history {
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

.chat-history::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.message {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.ai-avatar-img {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(0, 255, 136, 0.1);
  padding: 2px;
  box-sizing: border-box;
}

.user-avatar {
  background: #2a2a2a;
  color: #888;
  scale:1.3;
  border-radius: 50%;
}

.thinking-icon {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.message-content {
  flex: 1;
  max-width: calc(100% - 44px);
}

.message.user .message-content {
  text-align: right;
}

.message-text {
  background: #333;
  color: #fff;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.5;
  word-wrap: break-word;
  margin-bottom: 4px;
}

.message.user .message-text {
  background: #888;
  border-bottom-right-radius: 4px;
}

.message.ai .message-text {
  background: #333;
  border-bottom-left-radius: 4px;
}

.message-time {
  color: #888;
  font-size: 11px;
  margin-top: 4px;
}

.thinking-dots {
  display: flex;
  gap: 4px;
  padding: 12px 16px;
  background: #2a2a2a;
  border-radius: 12px;
  border-bottom-left-radius: 4px;
}

.thinking-dots span {
  width: 6px;
  height: 6px;
  background: #888;
  border-radius: 50%;
  animation: thinking 1.4s ease-in-out infinite;
}

.thinking-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.thinking-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes thinking {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

.chat-input-area {
  padding: 12px;
  border-top: 1px solid #444;
  background: #2a2a2a;
  flex-shrink: 0;
}

.input-container {
  position: relative;
}

.input-container :deep(.el-textarea) {
  width: 100%;
}



.input-container :deep(.el-textarea__inner) {
  background: #333 !important;
  border: 1px solid #00ff88 !important;
  color: #fff !important;
  border-radius: 4px;
  resize: none;
  padding-right: 48px;
}

.input-container :deep(.el-textarea__inner):focus {
  border-color: #00ff88 !important;
  background: #333 !important;
  box-shadow: 0 0 0 2px rgba(0, 255, 136, 0.2) !important;
}

.input-container :deep(.el-textarea__inner):hover {
  background: #444 !important;
  border-color: #00ff88 !important;
}

.send-button {
  position: absolute;
  right: 8px;
  bottom: 8px;
  height: 32px;
  width: 32px;
  border-radius: 4px;
  background: transparent;
  border: none;
  color: #00ff88;
  padding: 0;
  min-height: auto;
  z-index: 10;
}

.send-button:hover:not(:disabled) {
  background: rgba(0, 255, 136, 0.1);
  color: #00ff88;
}
.b-icons {
  scale: 1.3;
  color: #00ff88;
}
.send-button:disabled {
  background: transparent;
  color: #666;
  cursor: not-allowed;
}


</style>