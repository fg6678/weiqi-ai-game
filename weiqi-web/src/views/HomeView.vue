<template>
  <main>
    <div class="game-container">
      <div class="system-header">
        <div class="system-info">
          <h1 class="game-title">Go AI Analysis System</h1>
          <div class="system-meta">
            <span class="meta-item">Engine: KataGo</span>
            <span class="meta-item">Board: 19×19</span>
            <span class="meta-item mode-clickable" @click.stop="switchGameMode()">Mode: {{ gameMode === 'human_vs_ai' ? 'Human vs AI' : '推演模式' }}</span>
          </div>
        </div>

        <div class="connection-status">
          <span :class="connectionStatusClass">{{ connectionStatusText }}</span>
        </div>
      </div>
      
      <div class="game-layout">
        <!-- 左侧面板：游戏控制和信息 -->
        <div class="left-panel">
          <!-- 游戏控制面板组件 -->
          <GameControlPanel
            :game-state="gameState"
            :game-settings="gameSettings"
            :suggestion-settings="suggestionSettings"
            :game-session-active="gameSessionActive"
            :ai-thinking="aiThinking"
            :territory-preview-active="territoryPreviewActive"
            :game-mode="gameMode"

            @toggle-game-session="toggleGameSession"
            @new-game="newGame"
            @undo-move="undoMove"
            @pass="pass"
            @player-color-change="onPlayerColorChange"
            @ai-strength-change="onAiStrengthChange"
            @komi-change="onKomiChange"
            @rules-change="onRulesChange"
            @suggestion-count-change="onSuggestionCountChange"
            @calculate-territory="calculateTerritory"
            @territory-preview="toggleTerritoryPreview"
            @import-sgf="importSgfFile"

          />

          <!-- 游戏信息面板组件 -->
          <GameInfoPanel
            ref="gameInfoPanel"
            :game-state="gameState"
            :black-winrate="blackWinrate"
            :white-winrate="whiteWinrate"
            :ai-analysis="aiAnalysis"

            @go-to-move="goToMove"
          />
        </div>
        
        <div class="board-section">
          <WeiQiBoard
            v-if="gameState.board"
            :board="gameState.board"
            :moves="gameState.moves"
            :current-player="gameState.current_player"
            :game-over="gameState.game_over"
            :move-count="gameState.move_count"
            :ai-thinking="aiThinking"
            :ai-analysis="aiAnalysis"
            :show-ai-suggestions="showAiSuggestions"
            :displayed-analysis="displayedAnalysis"
            :game-settings="{...gameSettings, gameMode: gameMode}"
            :territory-data="territoryData"

            @make-move="makeMove"
            @new-game="newGame"
          />
          <div v-else class="loading-board">
            <div class="loading-text">正在初始化棋盘...</div>
          </div>
        </div>
        
        <div class="right-panel">
          <!-- 对局故事线模块 - 暂时隐藏 -->
          <!-- <div class="story-section">
            <GameStoryPanel
              :game-state="gameState"
            />
          </div> -->
          
          <!-- AI讲棋模块 - 铺满整个右边 -->
          <div class="ai-commentary-section full-height">
            <AICommentaryPanel
              ref="aiCommentaryPanel"
              :game-state="gameState"
              @send-message="handleAIMessage"
            />
          </div>
        </div>
      </div>
    </div>
    
    <div class="error-message" v-if="errorMessage">
      {{ errorMessage }}
    </div>
  </main>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import WeiQiBoard from '@/components/WeiQiBoard.vue'
import GameControlPanel from '@/components/GameControlPanel.vue'
import GameInfoPanel from '@/components/GameInfoPanel.vue'
import AICommentaryPanel from '@/components/AICommentaryPanel.vue'
import GameStoryPanel from '@/components/GameStoryPanel.vue'
import {
  CommandLineIcon,
  DocumentTextIcon,
  ArrowUturnLeftIcon,
  ForwardIcon,
  PlusIcon,
  InformationCircleIcon,
  PlayIcon,
  StopIcon
} from '@heroicons/vue/24/outline'

const gameState = ref({
  board: Array(19).fill(null).map(() => Array(19).fill(0)),
  moves: [],
  current_player: 'B',
  game_over: false,
  move_count: 0,
  captured_black: 0,
  captured_white: 0
})

// AI推荐选点控制
const suggestionSettings = ref({
  count: 5
})



// 游戏设置
// 游戏模式
const gameMode = ref('human_vs_ai') // 'human_vs_ai' 或 'analysis'

const gameSettings = ref({
  playerColor: 'B',  // 玩家执子颜色
  aiStrength: 3,     // AI算力（秒数）
  suggestionAiStrength: 3, // 推荐选点AI算力（秒数）
  komi: 6.5,         // 贴目
  rules: 'chinese'   // 规则
})

// 根据选点数量自动计算是否显示AI推荐
const showAiSuggestions = computed(() => {
  return parseInt(suggestionSettings.value.count) > 0
})

// 游戏会话状态
const gameSessionActive = ref(false)

// 领地预览数据
const territoryData = ref(null)
const territoryPreviewActive = ref(false)

// 胜率数据
const blackWinrate = ref(50.0)
const whiteWinrate = ref(50.0)

// 显示的AI分析数据
const displayedAnalysis = computed(() => {
  if (!showAiSuggestions.value) {
    return []
  }
  
  const count = parseInt(suggestionSettings.value.count)
  
  // 使用静态分析数据
  if (topAnalysis.value.length > 0) {
    return topAnalysis.value.slice(0, count)
  }
  
  return []
})

// 最近的着法历史（限制显示数量）
const recentMoves = computed(() => {
  const maxMoves = 20
  const moves = gameState.value.moves
  const startIndex = Math.max(0, moves.length - maxMoves)
  
  return moves.slice(startIndex).map((move, index) => ({
    number: startIndex + index + 1,
    color: move[0],
    position: move[1]
  }))
})

// AI分析的滚动窗口限制
const topAnalysis = computed(() => {
  const maxAnalysis = 5
  return aiAnalysis.value.slice(0, maxAnalysis)
})

const aiThinking = ref(false)
const aiAnalysis = ref([])
const errorMessage = ref('')
const ws = ref(null)

// 分支模式相关状态已移除 - 使用简单回溯机制
// 移除了lastMove，不再需要实时更新逻辑



// AI讲棋相关方法
function handleAIMessage(message) {
  // 处理AI讲棋消息
  console.log('AI Commentary:', message)
  
  if (ws.value && ws.value.readyState === WebSocket.OPEN) {
    if (message.type === 'change_model') {
      // 处理模型切换
      ws.value.send(JSON.stringify({
        type: 'change_model',
        model: message.model,
        gameState: message.gameState
      }))
    } else {
      // 处理其他AI讲棋消息
      ws.value.send(JSON.stringify({
        type: 'ai_commentary',
        message_type: message.type,
        move: message.move,
        message: message.message,
        gameState: message.gameState
      }))
    }
  }
}

// 处理AI讲棋回复
function handleAICommentaryResponse(data) {
  if (aiCommentaryPanel.value) {
    aiCommentaryPanel.value.receiveAIMessage(data.content)
  }
}

// AI讲棋面板引用
const aiCommentaryPanel = ref(null)

// 游戏信息面板引用
const gameInfoPanel = ref(null)

// 连接状态
const connectionStatus = ref('disconnected')

const connectionStatusClass = computed(() => ({
  'status-connecting': connectionStatus.value === 'connecting',
  'status-connected': connectionStatus.value === 'connected',
  'status-disconnected': connectionStatus.value === 'disconnected'
}))

const connectionStatusText = computed(() => {
  switch (connectionStatus.value) {
    case 'connecting': return '连接中...'
    case 'connected': return '已连接'
    case 'disconnected': return '未连接'
    default: return '未知状态'
  }
})

// WebSocket 连接
function connectWebSocket() {
  try {
    connectionStatus.value = 'connecting'
    const sessionId = Math.random().toString(36).substring(2, 15)
    ws.value = new WebSocket(`ws://localhost:8000/ws/${sessionId}`)
    
    ws.value.onopen = () => {
      connectionStatus.value = 'connected'
      errorMessage.value = ''
      console.log('WebSocket连接已建立，session_id:', sessionId)
    }
    
    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'game_state') {
          // 安全地更新游戏状态，确保必要的属性存在
          if (data.data && data.data.board) {
            // 安全地处理board数据
            let safeBoard
            try {
              if (Array.isArray(data.data.board) && data.data.board.length === 19) {
                safeBoard = data.data.board.map(row => {
                  if (Array.isArray(row) && row.length === 19) {
                    return row
                  } else {
                    return Array(19).fill(0)
                  }
                })
              } else {
                safeBoard = Array(19).fill(null).map(() => Array(19).fill(0))
              }
            } catch (error) {
              console.error('处理board数据时出错:', error)
              safeBoard = Array(19).fill(null).map(() => Array(19).fill(0))
            }
            
            gameState.value = {
              board: safeBoard,
              moves: data.data.moves || [],
              current_player: data.data.current_player || 'B',
              game_over: data.data.game_over || false,
              move_count: data.data.move_count || 0,
              captured_black: data.data.captured_black || 0,
              captured_white: data.data.captured_white || 0,
              winrate_history: data.data.winrate_history || []
            }
            // 直接从游戏状态的胜率历史中获取最新胜率
            updateWinratesFromGameState()
          }
        } else if (data.type === 'ai_analysis') {
          aiAnalysis.value = data.data
          aiThinking.value = false
          // 优先从游戏状态更新胜率，如果没有则使用AI分析数据
          if (gameState.value.winrate_history && gameState.value.winrate_history.length > 0) {
            updateWinratesFromGameState()
          } else {
            updateWinrates(data.data)
          }

        } else if (data.type === 'ai_thinking') {
          aiThinking.value = data.thinking
        } else if (data.type === 'setting_changed') {
          // 处理设置变更消息
          console.log(`设置已更新: ${data.message}`)
          // 可以在这里添加用户提示，比如显示一个临时的成功消息
          errorMessage.value = '' // 清除错误消息
        } else if (data.type === 'ai_commentary_response') {
          handleAICommentaryResponse(data)
        } else if (data.type === 'model_changed') {
          // 处理模型切换确认消息
          console.log('模型切换成功:', data.model)
          if (aiCommentaryPanel.value) {
            aiCommentaryPanel.value.receiveAIMessage(`模型已切换为 ${data.model}`)
          }
        } else if (data.type === 'territory_score_response') {
          handleTerritoryScore(data)
        } else if (data.type === 'territory_preview_response') {
          handleTerritoryPreview(data)
        } else if (data.type === 'sgf_import_success') {
          // 处理SGF导入成功消息
          ElMessage.success(data.message || 'SGF文件导入成功')
          errorMessage.value = '' // 清除错误消息
          
          // SGF导入成功后，如果AI选点数量大于0，则请求推荐选点
          if (suggestionSettings.value.count > 0) {
            console.log('SGF导入成功，请求AI推荐选点')
            sendMessage({
              type: 'get_ai_suggestions'
            })
          }
        } else if (data.type === 'error') {
          errorMessage.value = data.message
          aiThinking.value = false
        }
      } catch (error) {
        errorMessage.value = '消息解析错误'
      }
    }
    
    ws.value.onerror = (error) => {
      connectionStatus.value = 'disconnected'
      errorMessage.value = 'WebSocket 连接错误'
    }
    
    ws.value.onclose = () => {
      connectionStatus.value = 'disconnected'
      // 尝试重连
      setTimeout(() => {
        if (connectionStatus.value === 'disconnected') {
          connectWebSocket()
        }
      }, 3000)
    }
  } catch (error) {
    connectionStatus.value = 'disconnected'
    errorMessage.value = 'WebSocket 连接失败'
  }
}

// 发送消息
function sendMessage(message) {
  console.log('sendMessage called with:', message)
  console.log('WebSocket状态检查:', {
    wsExists: !!ws.value,
    readyState: ws.value ? ws.value.readyState : 'null',
    isOpen: ws.value && ws.value.readyState === WebSocket.OPEN
  })
  
  if (ws.value && ws.value.readyState === WebSocket.OPEN) {
    const messageStr = JSON.stringify(message)
    console.log('发送WebSocket消息:', messageStr)
    ws.value.send(messageStr)
    console.log('WebSocket消息已发送')
  } else {
    console.log('WebSocket连接未建立，无法发送消息')
    errorMessage.value = 'WebSocket 连接未建立'
  }
}

// 落子
function makeMove(position) {
  // 检查游戏状态是否有效
  if (!gameState.value.board || gameState.value.game_over) {
    if (!gameState.value.board) {
      errorMessage.value = '棋盘未初始化，请稍候再试'
    }
    return
  }
  
  // 在Human vs AI模式下，检查是否轮到玩家
  if (gameMode.value === 'human_vs_ai' && (gameState.value.current_player !== gameSettings.value.playerColor || aiThinking.value)) {
    return
  }
  
  // 分支着法记录逻辑已移除 - 使用简单回溯机制
  
  // 自动关闭领地预览
  if (territoryData.value) {
    territoryData.value = null
  }
  
  // 清除之前的AI分析数据
  aiAnalysis.value = []
  
  // 在推演模式下不设置AI思考状态
  if (gameMode.value === 'human_vs_ai') {
    aiThinking.value = true
  }
  
  console.log('发送make_move消息，game_mode:', gameMode.value)
  sendMessage({
    type: 'make_move',
    move: position,
    game_mode: gameMode.value
  })
}

// 过手
function pass() {
  // 检查游戏状态是否有效
  if (!gameState.value.board || gameState.value.game_over) {
    if (!gameState.value.board) {
      errorMessage.value = '棋盘未初始化，请稍候再试'
    }
    return
  }
  
  // 在Human vs AI模式下，检查是否轮到玩家
  if (gameMode.value === 'human_vs_ai' && (gameState.value.current_player !== gameSettings.value.playerColor || aiThinking.value)) {
    return
  }
  
  // 在推演模式下，如果在分支模式中pass，继续保持分支状态
  // 不自动进入if模式，只有用户主动操作才进入
  
  // 自动关闭领地预览
  if (territoryData.value) {
    territoryData.value = null
  }
  
  // 清除之前的AI分析数据
  aiAnalysis.value = []
  
  // 在推演模式下不设置AI思考状态
  if (gameMode.value === 'human_vs_ai') {
    aiThinking.value = true
  }
  
  sendMessage({
    type: 'make_move',
    move: 'pass',
    game_mode: gameMode.value
  })
}

// 回溯到指定着法
function goToMove(moveIndex) {
  // 终止当前AI思考
  aiThinking.value = false
  
  // 清除之前的AI分析数据
  aiAnalysis.value = []
  
  // 清除领地预览数据
  territoryData.value = null
  
  // 发送回溯请求 - 简单回溯，删除指定手数后的所有着法
  if (ws.value && ws.value.readyState === WebSocket.OPEN) {
    ws.value.send(JSON.stringify({ 
      type: 'goto_move', 
      move_index: moveIndex 
    }))
    
    // 滚动胜率图表到回溯位置
    if (gameInfoPanel.value && gameInfoPanel.value.scrollToMove) {
      // 延迟一点时间等待数据更新后再滚动
      setTimeout(() => {
        gameInfoPanel.value.scrollToMove(moveIndex + 1) // moveIndex是0-based，转换为1-based
      }, 200)
    }
    
    // 在推演模式下，回溯后重新请求AI分析
    if (gameMode.value === 'analysis' && suggestionSettings.value.count > 0) {
      // 延迟一点时间等待棋盘状态更新后再请求分析
      setTimeout(() => {
        sendMessage({
          type: 'get_ai_suggestions'
        })
      }, 100)
    }
  }
}



// 新游戏
// 切换游戏会话状态
function toggleGameSession() {
  gameSessionActive.value = !gameSessionActive.value
  
  if (gameSessionActive.value) {
    // 开始对局时通知后端并自动开始新游戏
    sendMessage({
      type: 'start_game_session'
    })
    newGame()
  } else {
    // 终止对局时通知后端并清除状态
    sendMessage({
      type: 'stop_game_session'
    })
    aiAnalysis.value = []
    aiThinking.value = false
    errorMessage.value = ''
  }
}

function newGame() {
  if (!gameSessionActive.value) {
    errorMessage.value = '请先开始对局'
    return
  }
  
  // 清除之前的AI分析数据
  aiAnalysis.value = []
  
  console.log('发送new_game消息，game_mode:', gameMode.value)
  sendMessage({
    type: 'new_game',
    game_mode: gameMode.value
  })
}

// 悔棋
function undoMove() {
  if (gameState.value.move_count === 0 || gameState.value.game_over || aiThinking.value) {
    return
  }
  
  // 清除之前的AI分析数据
  aiAnalysis.value = []
  
  sendMessage({
    type: 'undo_move'
  })
}

// 模式切换函数
function switchGameMode(mode) {
  console.log('switchGameMode called with mode:', mode)
  console.log('current gameMode.value:', gameMode.value)
  
  if (mode) {
    gameMode.value = mode
  } else {
    // 如果没有指定模式，则切换到另一个模式
    gameMode.value = gameMode.value === 'human_vs_ai' ? 'analysis' : 'human_vs_ai'
  }
  
  console.log('切换到模式:', gameMode.value)
  
  // 界面初始化：清除所有对局信息
  initializeInterface()
  
  // 强制触发响应式更新
  console.log('模式切换完成，当前模式:', gameMode.value)
}

// 界面初始化函数：清除所有对局信息
function initializeInterface() {
  console.log('开始界面初始化，清除所有对局信息')
  
  // 重置游戏状态到初始状态
  gameState.value = {
    board: Array(19).fill(null).map(() => Array(19).fill(0)),
    moves: [],
    current_player: 'B',
    game_over: false,
    move_count: 0,
    captured_black: 0,
    captured_white: 0,
    winrate_history: []
  }
  
  // 清除AI分析数据
  aiAnalysis.value = []
  
  // 清除AI思考状态
  aiThinking.value = false
  
  // 清除错误消息
  errorMessage.value = ''
  
  // 清除领地预览数据
  territoryData.value = null
  
  // 重置胜率数据
  blackWinrate.value = 50.0
  whiteWinrate.value = 50.0
  
  // 重置AI讲棋面板的聊天记录
  if (aiCommentaryPanel.value) {
    aiCommentaryPanel.value.resetChatMessages()
  }
  
  // 重置游戏信息面板
  if (gameInfoPanel.value) {
    gameInfoPanel.value.resetGameInfo()
  }
  
  // 停止游戏会话（如果正在进行）
  if (gameSessionActive.value) {
    gameSessionActive.value = false
    sendMessage({
      type: 'stop_game_session'
    })
  }
  
  console.log('界面初始化完成')
}

// 计算终局点目
function calculateTerritory() {
  if (!gameSessionActive.value || aiThinking.value) {
    return
  }
  
  sendMessage({
    type: 'calculate_territory_score'
  })
}

// 领地预览
function territoryPreview() {
  console.log('territoryPreview called, gameSessionActive:', gameSessionActive.value, 'aiThinking:', aiThinking.value)
  console.log('WebSocket状态:', ws.value ? ws.value.readyState : 'null')
  
  // 只检查AI是否在思考，移除游戏会话检查
  if (aiThinking.value) {
    console.log('territoryPreview blocked: aiThinking=', aiThinking.value)
    return
  }
  
  // 如果当前已经显示领地预览，则清除显示
  if (territoryData.value) {
    console.log('clearing territory data')
    territoryData.value = null
    return
  }
  
  console.log('sending get_territory_preview message')
  console.log('WebSocket连接状态:', ws.value && ws.value.readyState === WebSocket.OPEN ? '已连接' : '未连接')
  
  const message = {
    type: 'get_territory_preview'
  }
  console.log('准备发送的消息:', message)
  sendMessage(message)
}

// 领地预览切换
const toggleTerritoryPreview = () => {
  territoryPreviewActive.value = !territoryPreviewActive.value
  
  if (territoryPreviewActive.value) {
    // 开启领地预览
    sendMessage({
      type: 'get_territory_preview'
    })
  } else {
    // 关闭领地预览
    territoryData.value = null
  }
}

// SGF文件导入
const importSgfFile = (sgfContent) => {
  if (!gameSessionActive.value) {
    errorMessage.value = '请先开始游戏会话'
    return
  }
  
  if (gameMode.value !== 'analysis') {
    errorMessage.value = 'SGF导入功能仅在推演模式下可用'
    return
  }
  
  sendMessage({
    type: 'import_sgf',
    sgf_content: sgfContent
  })
}

// 处理点目计算结果
function handleTerritoryScore(data) {
  console.log('收到点目计算响应:', data)
  
  if (data.result) {
    const result = data.result
    // 使用浏览器原生alert显示结果
    const message = `终局点目计算结果：\n黑棋总分：${result.black_score}\n白棋总分：${result.white_score}\n分数差：${result.score_difference}\n胜者：${result.winner}`
    
    alert(message)
  } else if (data.error) {
    errorMessage.value = data.error
  } else {
    errorMessage.value = '点目计算失败'
  }
}

// 处理领地预览结果
function handleTerritoryPreview(data) {
  console.log('收到领地预览响应:', data)
  console.log('data.result:', data.result)
  console.log('data.error:', data.error)
  console.log('完整的data对象:', JSON.stringify(data, null, 2))
  
  try {
    // 检查data.result是否存在且有success字段
    if (data.result) {
      console.log('data.result.success:', data.result.success)
      if (data.result.success) {
        // 安全地处理领地数据
        let safeTerritoryData = { ...data.result }
        
        // 验证ownership数据格式
        if (safeTerritoryData.ownership) {
          if (Array.isArray(safeTerritoryData.ownership) && safeTerritoryData.ownership.length === 19) {
            safeTerritoryData.ownership = safeTerritoryData.ownership.map(row => {
              if (Array.isArray(row) && row.length === 19) {
                return row
              } else {
                console.warn('领地数据行格式不正确，使用默认值')
                return Array(19).fill(0)
              }
            })
          } else {
            console.warn('领地数据格式不正确，清除ownership数据')
            delete safeTerritoryData.ownership
          }
        }
        
        // 将领地数据保存到状态中，传递给棋盘组件进行可视化显示
        territoryData.value = safeTerritoryData
        console.log('领地预览数据已更新：', safeTerritoryData)
      } else {
        console.log('领地预览失败，result.success为false')
        errorMessage.value = data.result.error || '领地预览失败'
        territoryData.value = null
      }
    } else if (data.error) {
      console.log('领地预览失败，错误信息:', data.error)
      errorMessage.value = data.error || '领地预览失败'
      territoryData.value = null
    } else {
      console.log('未知的领地预览响应格式')
      errorMessage.value = '领地预览响应格式错误'
      territoryData.value = null
    }
  } catch (error) {
    console.error('处理领地预览数据时出错:', error)
    errorMessage.value = '领地预览数据处理失败'
    territoryData.value = null
  }
}



// 推荐选点数量变化处理
function onSuggestionCountChange() {
  // 推荐选点数量变化时的处理逻辑
  console.log('推荐选点数量已更改为:', suggestionSettings.value.count)
}

// 从游戏状态的胜率历史中更新胜率数据
function updateWinratesFromGameState() {
  const winrateHistory = gameState.value.winrate_history || []
  if (winrateHistory.length > 0) {
    // 获取最新的胜率数据
    const latestWinrate = winrateHistory[winrateHistory.length - 1]
    if (latestWinrate && typeof latestWinrate.black_winrate === 'number') {
      // 确保胜率在有效范围内
      const blackWinrateValue = Math.max(0, Math.min(100, latestWinrate.black_winrate))
      blackWinrate.value = Math.round(blackWinrateValue * 10) / 10
      whiteWinrate.value = Math.round((100 - blackWinrateValue) * 10) / 10
    } else {
      // 如果胜率数据无效，使用默认值
      blackWinrate.value = 50.0
      whiteWinrate.value = 50.0
    }
  } else {
    // 如果没有胜率历史，使用默认值
    blackWinrate.value = 50.0
    whiteWinrate.value = 50.0
  }
  
  // 移除了lastMove更新逻辑，改为纯一问一答模式
}

// 更新胜率数据（保留原有的AI分析更新逻辑作为备用）
function updateWinrates(analysis) {
  if (analysis && analysis.length > 0) {
    // 使用最佳着法的胜率
    const bestMove = analysis[0]
    if (bestMove && typeof bestMove.winrate === 'number') {
      // KataGo返回的胜率是0-1之间的小数，需要转换为百分比
      let winratePercent = bestMove.winrate > 1 ? bestMove.winrate : bestMove.winrate * 100
      
      // KataGo配置中reportAnalysisWinratesAs = SIDETOMOVE
      // 返回的胜率是当前下棋方的胜率，需要转换为黑棋胜率
      let blackWinratePercent
      if (gameState.value.current_player === 'B') {
        // 当前是黑棋回合，KataGo返回的是黑棋胜率
        blackWinratePercent = winratePercent
      } else {
        // 当前是白棋回合，KataGo返回的是白棋胜率，需要转换为黑棋胜率
        blackWinratePercent = 100 - winratePercent
      }
      
      blackWinrate.value = Math.round(Math.max(0, Math.min(100, blackWinratePercent)) * 10) / 10
      whiteWinrate.value = Math.round((100 - blackWinrate.value) * 10) / 10
    }
  }
}

// 游戏设置处理函数
function onPlayerColorChange() {
  console.log('前端：玩家颜色改变为', gameSettings.value.playerColor)
  // 发送玩家颜色变更消息
  sendMessage({
    type: 'change_player_color',
    color: gameSettings.value.playerColor
  })
  console.log('前端：已发送change_player_color消息')
}

function onAiStrengthChange() {
  // 发送AI算力变更消息
  sendMessage({
    type: 'change_ai_strength',
    strength: gameSettings.value.aiStrength
  })
}

function onSuggestionAiStrengthChange() {
  // 发送推荐选点AI算力变更消息
  sendMessage({
    type: 'change_suggestion_ai_strength',
    strength: gameSettings.value.suggestionAiStrength
  })
}

function onKomiChange() {
  // 发送贴目变更消息
  sendMessage({
    type: 'change_komi',
    komi: gameSettings.value.komi
  })
  
  // 立即更新胜率显示以反映贴目变化
  if (aiAnalysis.value.length > 0) {
    updateWinrates(aiAnalysis.value)
  }
}

function onRulesChange() {
  // 发送规则变更消息
  sendMessage({
    type: 'change_rules',
    rules: gameSettings.value.rules
  })
}

// 组件挂载时连接 WebSocket
onMounted(() => {
  connectWebSocket()
})

// 组件卸载时关闭 WebSocket
onUnmounted(() => {
  if (ws.value) {
    ws.value.close()
  }
})
</script>

<style scoped>
.game-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  margin: 0;
  padding: 0;
  position: fixed;
  top: 0;
  left: 0;
  background: #1a1a1a;
  color: #e0e0e0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.system-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 20px;
  background: #2a2a2a;
  border-bottom: 1px solid #444;
  
}

.system-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.game-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #00ff88;
}

.system-meta {
  display: flex;
  gap: 20px;
  font-size: 12px;
  color: #888;
}

.meta-item {
  padding: 2px 8px;
  background: #333;
  border-radius: 3px;
}

/* 图标样式 */
.icon {
  width: 20px;
  height: 20px;
  display: inline-block;
}

.button-group .icon {
  width: 16px;
  height: 16px;
}

.control-header .icon {
  width: 16px;
  height: 16px;
}

.section-header .icon {
  width: 24px;
  height: 24px;
}

.info-item .icon {
  width: 14px;
  height: 14px;
}

.mode-switch {
  display: flex;
  gap: 8px;
  align-items: center;
}

.mode-btn {
  padding: 6px 12px;
  border: 1px solid #444;
  background: #333;
  color: #ccc;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.mode-btn:hover {
  background: #444;
  color: #fff;
}

.mode-btn.active {
  background: #00ff88;
  color: #000;
  border-color: #00ff88;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 500;
}

.status-connecting {
  color: #ffaa00;
}

.status-connected {
  color: #00ff88;
}

.status-disconnected {
  color: #ff4444;
}

.game-layout {
  display: flex;
  gap: 20px;
  height: calc(100vh - 120px);
  width: 100%;
  margin: 0;
  padding: 0 20px;
}

.left-panel {
  flex: 0 0 39vh;
  height: 100%; /* 与棋盘高度一致 */
  display: flex;
  margin-top: 20px;
  margin-left: 0;
  margin-right: 0;
  flex-direction: column;
  gap: 20px; /* 统一间距 */
  overflow: hidden;
}

.story-section {
  flex: 2;
  overflow: hidden;
}

.ai-commentary-section {
  flex: 3;
  overflow: hidden;
}

.ai-commentary-section.full-height {
  height: 100%;
  flex: 1;
}

.board-section {
  flex: 1;
  height: 100%; /* 与棋盘高度一致 */
  display: flex;
  margin-top: 20px;
  margin-left: 0;
  margin-right: 0;
  flex-direction: column;
  gap: 20px; /* 统一间距 */
  overflow: hidden;
}

.right-panel {
  flex: 0 0 61vh;
  margin-top: 20px;
  height: 100%; /* 与棋盘高度一致 */
  display: flex;
  margin-left: 0;
  margin-right: 0;
  flex-direction: column;
  gap: 20px; /* 统一间距 */
  overflow: hidden;
}

.control-section {
  flex: 0 0 auto;
  background: #2a2a2a;
  border: 1px solid #444;
  border-radius: 8px;
  padding: 0.8vh;
  max-height: 45vh; /* 调整最大高度 */
  overflow-y: auto;
}

.game-info-section {
  flex: 1;
  background: #2a2a2a;
  border: 1px solid #444;
  border-radius: 8px;
  padding: 1.5vh;
  overflow-y: hidden;
  min-height: 0;
  height: auto; /* 确保能够自适应剩余空间 */
}

.section-header {
  margin-bottom: 1.5vh;
  padding-bottom: 0.8vh;
  border-bottom: 0.1vh solid #444;
}

.section-header h3, .section-header h4 {
  margin: 0;
  font-size: 18px;
  color: #00ff88;
  font-weight: 600;
}

.status-display {
  margin-bottom: 1.8vh;
}

.current-player {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 15px;
}

.current-player span {
  padding: 0.6vh 1.2vw;
  border-radius: 0.6vh;
  transition: all 0.3s ease;
}

.current-player span.active {
  background: #00ff88;
  color: #000;
}

.vs {
  color: #888;
  font-size: 12px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  margin-bottom: 10px;
}

.move-count-text {
  font-size: 14px;
  color: #ccc;
  font-weight: 500;
}

.game-status, .ai-status {
  text-align: center;
  font-size: 14px;
}

.game-over {
  color: #ff4444;
  font-weight: bold;
}

.thinking {
  color: #ffaa00;
  font-weight: bold;
}

.control-buttons {
  margin-bottom: 1.8vh;
}

.button-row {
  display: flex;
  gap: 1vw;
  margin-bottom: 1vh;
}

.button-row:last-child {
  margin-bottom: 0;
}

.btn {
  flex: 1;
  padding: 1.2vh 1.5vw;
  border: none;
  border-radius: 0.8vh;
  font-size: 1.3rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.undo-btn {
  background: #ff6b35;
  color: #fff;
}

.undo-btn:hover:not(:disabled) {
  background: #ff5722;
}

.pass-btn {
  background: #444;
  color: #e0e0e0;
}

.pass-btn:hover:not(:disabled) {
  background: #555;
}

.new-game-btn {
  background: #00ff88;
  color: #000;
}

.new-game-btn:hover {
  background: #00cc6a;
}

.session-btn {
  background: #4CAF50;
  color: #fff;
}

.session-btn:hover:not(:disabled) {
  background: #45a049;
}

.session-btn.active {
  background: #f44336;
}

.session-btn.active:hover:not(:disabled) {
  background: #da190b;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 游戏设置样式 */
.game-settings {
  border-top: 0.1vh solid #444;
  padding-top: 1.5vh;
  margin-bottom: 1.5vh;
}

.setting-group {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1vh;
}

.setting-group:last-child {
  margin-bottom: 0;
}

.setting-label {
  font-size: 13px;
  color: #ccc;
  font-weight: 500;
  min-width: 60px;
}

.setting-select {
  padding: 8px 12px;
  border: 1px solid #555;
  border-radius: 4px;
  background: #1a1a1a;
  color: #e0e0e0;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 80px;
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  background-image: url('data:image/svg+xml;charset=US-ASCII,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 4 5"><path fill="%23888" d="M2 0L0 2h4zm0 5L0 3h4z"/></svg>');
  background-repeat: no-repeat;
  background-position: right 8px center;
  background-size: 12px;
  padding-right: 32px;
}

.setting-select:hover {
  background-color: #2a2a2a;
  border-color: #666;
}

.setting-select:focus {
  outline: none;
  border-color: #00ff88;
  background-color: #2a2a2a;
  box-shadow: 0 0 0 2px rgba(0, 255, 136, 0.2);
}

.slider-container {
  display: flex;
  flex-direction: column;
  gap: 0.5vh;
  min-width: 120px;
}

.setting-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 0.4vh;
  border-radius: 0.2vh;
  background: #333;
  outline: none;
  cursor: pointer;
}

.setting-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 1.6vh;
  height: 1.6vh;
  border-radius: 50%;
  background: #00ff88;
  cursor: pointer;
  transition: all 0.3s ease;
}

.setting-slider::-webkit-slider-thumb:hover {
  background: #00cc66;
  transform: scale(1.1);
}

.setting-slider::-moz-range-thumb {
  width: 1.6vh;
  height: 1.6vh;
  border-radius: 50%;
  background: #00ff88;
  cursor: pointer;
  border: none;
  transition: all 0.3s ease;
}

.setting-slider::-moz-range-thumb:hover {
  background: #00cc66;
  transform: scale(1.1);
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #888;
  margin-top: 0.2vh;
}

/* AI推荐控制样式 */
.ai-suggestions-control {
  border-top: 0.1vh solid #444;
  padding-top: 1.5vh;
}

/* 胜率图表样式 */
.winrate-chart {
  margin-bottom: 2vh;
}

.unified-winrate-display {
  display: flex;
  align-items: center;
  gap: 1vw;
  font-size: 1.4rem;
}

.winrate-left, .winrate-right {
  min-width: 5vw;
  text-align: center;
  font-size: 1.4rem;
  font-weight: 600;
}

.unified-winrate-bar {
  flex: 1;
  height: 2.5vh;
  background: linear-gradient(90deg, #f0f0f0, #ffffff);
  border: 1px solid #444;
  border-radius: 1.25vh;
  overflow: hidden;
  position: relative;
  display: flex;
}

.black-winrate-fill {
  background: linear-gradient(90deg, #1a1a1a, #333);
  transition: width 0.5s ease;
  height: 100%;
  border-radius: 1.25vh 0 0 1.25vh;
}

.white-winrate-fill {
  background: linear-gradient(270deg, #f0f0f0, #ffffff);
  transition: width 0.5s ease;
  height: 100%;
  border-left: 1px solid #ccc;
}

.black-percent {
  color: #666;
}

.white-percent {
  color: #ddd;
}

.info-panel {
  background: #2a2a2a;
  border: 0.1vh solid #444;
  border-radius: 1vh;
  padding: 1.8vh;
}

.move-history {
  margin-bottom: 2vh;
}

.move-history h4 {
  margin: 0 0 1vh 0;
  font-size: 1.4rem;
  color: #ccc;
}

.history-container {
  height: 25vh;
  overflow-y: auto;
  /* 隐藏滚动条 */
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE and Edge */
}

.history-container::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Opera */
}

.ai-analysis-panel h3 {
  color: #e0e0e0;
  margin: 0 0 1.2vh 0;
  font-size: 1.6rem;
  font-weight: 600;
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 1vh;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 1.4rem;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 0.5vh;
}

.history-list::-webkit-scrollbar {
  width: 0.8vw;
}

.history-list::-webkit-scrollbar-track {
  background: #1a1a1a;
  border-radius: 0.4vw;
}

.history-list::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 0.4vw;
}

.history-list::-webkit-scrollbar-thumb:hover {
  background: #777;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 1.2vw;
  padding: 1vh;
  background: #333;
  border-radius: 0.5vh;
  font-size: 1.2rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.history-item:hover {
  background: #444;
  transform: translateX(0.3vw);
}

.history-item.clickable {
  border-left: 0.4vh solid transparent;
}

.history-item.clickable:hover {
  border-left-color: #00ff88;
}

.history-item .move-number {
  color: #888;
  min-width: 3.5vw;
}

.history-item .move-color {
  font-size: 1.4rem;
  min-width: 2.5vw;
}

.history-item .move-position {
  color: #e0e0e0;
  font-weight: bold;
}

.label {
  color: #888;
  font-size: 1.2rem;
}

.value {
  color: #e0e0e0;
  font-weight: 500;
}

.error-message {
  position: fixed;
  top: 2vh;
  right: 2vw;
  background: #ff4444;
  color: white;
  padding: 1.2vh 1.8vw;
  border-radius: 0.6vh;
  font-size: 1.4rem;
  z-index: 1000;
}



.game-basic-info {
  margin-top: 2.5vh;
}

.game-basic-info h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  color: #ccc;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1vh;
}

.info-grid .info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.8vh 1vw;
  background: #333;
  border-radius: 0.5vh;
  font-size: 1.2rem;
}

.info-grid .label {
  color: #888;
}

.info-grid .value {
  color: #e0e0e0;
  font-weight: 500;
}

.loading-board {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 70vh;
  height: 70vh;
  background: #2a2a2a;
  border: 0.1vh solid #444;
  border-radius: 1vh;
}

.loading-text {
  color: #00ff88;
  font-size: 1.8rem;
  font-weight: 600;
}

/* 响应式设计 */
@media (max-width: 1400px) {
  .game-layout {
    grid-template-columns: 55vh 1fr 32vh;
    gap: 12px;
    padding: 0 15px;
  }
}

@media (max-width: 1200px) {
  .game-layout {
    grid-template-columns: 50vh 1fr 30vh;
    gap: 10px;
    padding: 0 10px;
  }
}

@media (max-width: 1000px) {
  .game-layout {
    grid-template-columns: 45vh 1fr 28vh;
    gap: 8px;
    padding: 0 8px;
  }
}

@media (max-width: 768px) {
  .game-layout {
    display: flex;
    flex-direction: column;
    padding: 1vh 1vw;
    gap: 15px;
  }
  
  .left-panel {
    order: 2;
  }
  
  .board-section {
    order: 1;
    max-width: none;
  }
  
  .right-panel {
    order: 3;
    flex: 1;
    max-width: none;
    min-width: auto;
  }
}

/* 可点击的模式标签样式 */
.mode-clickable {
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.3s ease;
  user-select: none;
}

.mode-clickable:hover {
  background: rgba(0, 123, 255, 0.1);
  color: #007bff;
}
</style>
