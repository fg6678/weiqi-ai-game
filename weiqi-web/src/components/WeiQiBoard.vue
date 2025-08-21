<template>
  <div class="weiqi-board-container" ref="boardContainer">
    <div class="board-wrapper">
      <svg 
        class="weiqi-board" 
        :width="boardSize" 
        :height="boardSize"
        @click="handleBoardClick"
      >
        <!-- 棋盘网格线 -->
        <defs>
          <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
            <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#8B4513" stroke-width="1"/>
          </pattern>
        </defs>
        
        <!-- 棋盘背景 -->
        <rect width="100%" height="100%" fill="#3a3a3a" />
        
        <!-- 网格线 -->
        <g v-for="i in 19" :key="'h' + i">
          <line 
            :x1="padding" 
            :y1="padding + (i - 1) * cellSize" 
            :x2="padding + 18 * cellSize" 
            :y2="padding + (i - 1) * cellSize" 
            stroke="#888" 
            stroke-width="1"
          />
        </g>
        <g v-for="i in 19" :key="'v' + i">
          <line 
            :x1="padding + (i - 1) * cellSize" 
            :y1="padding" 
            :x2="padding + (i - 1) * cellSize" 
             :y2="padding + 18 * cellSize" 
             stroke="#888" 
             stroke-width="1"
          />
        </g>
        
        <!-- 星位点 -->
        <circle 
          v-for="star in starPoints" 
          :key="star.x + '-' + star.y"
          :cx="padding + star.x * cellSize" 
          :cy="padding + star.y * cellSize" 
          r="3" 
          fill="#ccc"
        />
        
        <!-- 领地预览 -->
        <g v-if="territoryData && territoryData.ownership">
          <g v-for="(row, rowIndex) in territoryData.ownership" :key="'territory-' + rowIndex">
            <g v-for="(ownership, colIndex) in row" :key="'territory-' + rowIndex + '-' + colIndex">
              <rect 
                v-if="Math.abs(ownership) > 0.3"
                :x="padding + colIndex * cellSize - cellSize * 0.4" 
                :y="padding + rowIndex * cellSize - cellSize * 0.4" 
                :width="cellSize * 0.8" 
                :height="cellSize * 0.8"
                :fill="ownership > 0 ? 'rgba(0, 0, 0, 0.3)' : 'rgba(255, 255, 255, 0.3)'"
                :opacity="Math.abs(ownership)"
                class="territory-marker"
              />
            </g>
          </g>
        </g>
        
        <!-- 棋子 -->
        <g v-for="(row, rowIndex) in board" :key="rowIndex">
          <g v-for="(cell, colIndex) in row" :key="colIndex">
            <circle 
              v-if="cell !== 0"
              :cx="padding + colIndex * cellSize" 
              :cy="padding + rowIndex * cellSize" 
              :r="cellSize * 0.4"
              :fill="cell === 1 ? '#000' : '#fff'"
              :stroke="cell === 1 ? '#333' : '#ccc'"
              stroke-width="1"
              class="stone"
            />
          </g>
        </g>
        
        <!-- 最后一手标记 -->
        <circle 
          v-if="lastMove.row !== -1 && lastMove.col !== -1"
          :cx="padding + lastMove.col * cellSize" 
          :cy="padding + lastMove.row * cellSize" 
          :r="cellSize * 0.15"
          :fill="lastMove.color === 1 ? '#fff' : '#000'"
          class="last-move-marker"
        />
        
        <!-- 点击区域 -->
        <g v-for="(row, rowIndex) in board" :key="'click-' + rowIndex">
          <g v-for="(cell, colIndex) in row" :key="'click-' + rowIndex + '-' + colIndex">
            <circle 
              :cx="padding + colIndex * cellSize" 
              :cy="padding + rowIndex * cellSize" 
              :r="cellSize * 0.45"
              fill="transparent"
              class="click-area"
              @click="handlePointClick(rowIndex, colIndex)"
              @mouseenter="handlePointHover(rowIndex, colIndex)"
              @mouseleave="handleMouseLeave"
            />
          </g>
        </g>
        
        <!-- 悬停预览 -->
        <circle 
          v-if="hoverPosition.row !== -1 && hoverPosition.col !== -1 && !gameOver"
          :cx="padding + hoverPosition.col * cellSize" 
          :cy="padding + hoverPosition.row * cellSize" 
          :r="cellSize * 0.4"
          :fill="getBranchModeHoverFill()"
          class="hover-stone"
        />
        
        <!-- AI推荐着法标记 -->
        <g v-if="showAiSuggestions && displayedAnalysis && displayedAnalysis.length > 0">
          <g v-for="(suggestion, index) in displayedAnalysis.slice(0, 5)" :key="'suggestion-' + index">
            <template v-if="getSuggestionPosition(suggestion.move)">
              <!-- 推荐位置圆圈 -->
              <circle 
                :cx="padding + getSuggestionPosition(suggestion.move).col * cellSize" 
                :cy="padding + getSuggestionPosition(suggestion.move).row * cellSize" 
                :r="cellSize * 0.3"
                fill="rgba(255, 165, 0, 0.7)"
                stroke="#ff8c00"
                stroke-width="2"
                class="ai-suggestion"
              />
              <!-- 推荐序号 -->
              <text 
                :x="padding + getSuggestionPosition(suggestion.move).col * cellSize" 
                :y="padding + getSuggestionPosition(suggestion.move).row * cellSize + 2" 
                text-anchor="middle"
                font-family="Arial, sans-serif"
                font-size="12"
                font-weight="bold"
                fill="#fff"
                class="suggestion-number"
              >
                {{ index + 1 }}
              </text>
              <!-- 胜率信息 -->
              <text 
                :x="padding + getSuggestionPosition(suggestion.move).col * cellSize" 
                :y="padding + getSuggestionPosition(suggestion.move).row * cellSize - 18" 
                text-anchor="middle"
                font-family="Arial, sans-serif"
                font-size="10"
                font-weight="bold"
                fill="#ffaa00"
                class="suggestion-winrate"
              >
                {{ getAdjustedWinrate(suggestion.winrate) }}%
              </text>
              <!-- 得分信息 -->
              <text 
                :x="padding + getSuggestionPosition(suggestion.move).col * cellSize" 
                :y="padding + getSuggestionPosition(suggestion.move).row * cellSize + 25" 
                text-anchor="middle"
                font-family="Arial, sans-serif"
                font-size="9"
                font-weight="bold"
                fill="#888"
                class="suggestion-score"
              >
                {{ suggestion.score_lead > 0 ? '+' : '' }}{{ suggestion.score_lead.toFixed(1) }}
              </text>
            </template>
          </g>
        </g>
        
        <!-- 提子动画效果 -->
        <g v-for="capture in capturedStones" :key="capture.id">
          <circle 
            :cx="padding + capture.col * cellSize" 
            :cy="padding + capture.row * cellSize" 
            :r="cellSize * 0.4"
            :fill="capture.color === 1 ? '#000' : '#fff'"
            :stroke="capture.color === 1 ? '#333' : '#ccc'"
            stroke-width="1"
            class="captured-stone"
          />
        </g>
      </svg>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps([
  'board',
  'moves', 
  'currentPlayer',
  'gameOver',
  'moveCount',
  'aiThinking',
  'aiAnalysis',
  'showAiSuggestions',
  'displayedAnalysis',
  'gameSettings',
  'territoryData',

])

const emit = defineEmits(['makeMove', 'newGame'])

// 使用响应式计算棋盘尺寸
const boardContainer = ref(null)
const cellSize = ref(42)
const padding = ref(25)
const boardSize = computed(() => 18 * cellSize.value + 2 * padding.value)
const hoverPosition = ref({ row: -1, col: -1 })
const capturedStones = ref([])

// 星位点坐标 (0-18索引)
const starPoints = [
  { x: 3, y: 3 }, { x: 9, y: 3 }, { x: 15, y: 3 },
  { x: 3, y: 9 }, { x: 9, y: 9 }, { x: 15, y: 9 },
  { x: 3, y: 15 }, { x: 9, y: 15 }, { x: 15, y: 15 }
]

// 最后一手的位置
const lastMove = computed(() => {
  if (props.moves.length === 0) {
    return { row: -1, col: -1, color: 0 }
  }
  
  const lastMoveData = props.moves[props.moves.length - 1]
  const position = lastMoveData[1]
  
  if (position === 'pass') {
    return { row: -1, col: -1, color: 0 }
  }
  
  const col = parsePosition(position).col
  const row = parsePosition(position).row
  const color = lastMoveData[0] === 'B' ? 1 : 2
  
  return { row, col, color }
})

// 解析棋子位置
function parsePosition(position) {
  if (position === 'pass' || position.length < 2) {
    return { row: -1, col: -1 }
  }
  
  const colChar = position[0]
  const rowStr = position.slice(1)
  const colLetters = 'ABCDEFGHJKLMNOPQRST'
  
  const col = colLetters.indexOf(colChar)
  const row = parseInt(rowStr) - 1
  
  if (col === -1 || isNaN(row) || row < 0 || row >= 19 || col < 0 || col >= 19) {
    return { row: -1, col: -1 }
  }
  
  return { row, col }
}

// 将坐标转换为棋谱位置
function positionToString(row, col) {
  const colLetters = 'ABCDEFGHJKLMNOPQRST'
  return colLetters[col] + (row + 1)
}

// 获取AI推荐着法的位置
function getSuggestionPosition(move) {
  if (!move || move === 'pass') {
    return null
  }
  
  const position = parsePosition(move)
  if (position.row === -1 || position.col === -1) {
    return null
  }
  
  // 检查位置是否已有棋子
  if (props.board && props.board[position.row] && props.board[position.row][position.col] !== 0) {
    return null
  }
  
  return position
}

// 获取调整后的胜率（考虑贴目）
function getAdjustedWinrate(winrate) {
  if (!props.gameSettings) {
    return (winrate * 100).toFixed(0)
  }
  
  let winratePercent = winrate > 1 ? winrate : winrate * 100
  
  // 根据贴目调整胜率显示
  const komiAdjustment = (props.gameSettings.komi - 6.5) * 2
  
  if (props.currentPlayer === 'B') {
    // 黑棋回合，调整黑棋胜率
    const adjustedWinrate = winratePercent - komiAdjustment
    return Math.round(Math.max(0, Math.min(100, adjustedWinrate)))
  } else {
    // 白棋回合，调整白棋胜率
    const adjustedWinrate = winratePercent + komiAdjustment
    return Math.round(Math.max(0, Math.min(100, adjustedWinrate)))
  }
}

// 获取悬停填充颜色
function getBranchModeHoverFill() {
  return props.currentPlayer === 'B' ? 'rgba(0, 0, 0, 0.3)' : 'rgba(255, 255, 255, 0.5)'
}

// 处理点击交叉点
function handlePointClick(row, col) {
  // 推演模式下允许自由落子，不检查玩家颜色
  const isAnalysisMode = props.gameSettings?.gameMode === 'analysis'
  
  if (props.gameOver || props.aiThinking) {
    return
  }
  
  // 在Human vs AI模式下检查是否轮到玩家
  if (!isAnalysisMode && props.currentPlayer !== props.gameSettings?.playerColor) {
    return
  }
  

  
  // 检查位置是否已有棋子
  if (props.board[row][col] !== 0) {
    return
  }
  
  const position = positionToString(row, col)
  emit('makeMove', position)
}

// 处理点悬停
function handlePointHover(row, col) {
  // 推演模式下允许自由悬停预览
  const isAnalysisMode = props.gameSettings?.gameMode === 'analysis'
  
  if (props.gameOver || props.aiThinking) {
    hoverPosition.value = { row: -1, col: -1 }
    return
  }
  
  // 在Human vs AI模式下检查是否轮到玩家
  if (!isAnalysisMode && props.currentPlayer !== props.gameSettings?.playerColor) {
    hoverPosition.value = { row: -1, col: -1 }
    return
  }
  

  
  // 检查位置是否已有棋子
  if (props.board[row][col] !== 0) {
    hoverPosition.value = { row: -1, col: -1 }
    return
  }
  
  hoverPosition.value = { row, col }
}



function handleMouseLeave() {
  hoverPosition.value = { row: -1, col: -1 }
}

// 过
function pass() {
  // 推演模式下允许自由过手
  const isAnalysisMode = props.gameSettings?.gameMode === 'analysis'
  
  if (props.gameOver || props.aiThinking) {
    return
  }
  
  // 在Human vs AI模式下检查是否轮到玩家
  if (!isAnalysisMode && props.currentPlayer !== props.gameSettings?.playerColor) {
    return
  }
  
  emit('makeMove', 'pass')
}

// 新游戏
function newGame() {
  emit('newGame')
}

// 监听棋盘变化，检测提子
watch(() => props.board, (newBoard, oldBoard) => {
  if (!oldBoard) return
  
  // 检测被提取的棋子
  const captured = []
  
  for (let row = 0; row < 19; row++) {
    for (let col = 0; col < 19; col++) {
      // 如果原来有棋子，现在没有了，说明被提取了
      if (oldBoard[row][col] !== 0 && newBoard[row][col] === 0) {
        captured.push({
          id: `capture-${Date.now()}-${row}-${col}`,
          row,
          col,
          color: oldBoard[row][col]
        })
      }
    }
  }
  
  if (captured.length > 0) {
    // 显示提子动画
    capturedStones.value = captured
    
    // 800ms后清除动画
    setTimeout(() => {
      capturedStones.value = []
    }, 800)
  }
}, { deep: true })

// 响应式调整棋盘大小，优化尺寸计算
const updateBoardSize = () => {
  if (boardContainer.value) {
    const containerHeight = boardContainer.value.clientHeight
    const containerWidth = boardContainer.value.clientWidth
    
    // 计算可用空间，考虑board-wrapper的padding和边框
    const wrapperPadding = 20 // 固定padding值
    const borderWidth = 2 // 边框宽度
    const availableHeight = containerHeight - wrapperPadding * 2 - borderWidth * 2
    const availableWidth = containerWidth - wrapperPadding * 2 - borderWidth * 2
    
    // 取较小值确保棋盘完全显示
    const maxBoardSize = Math.min(availableHeight, availableWidth)
    
    // 计算格子大小：棋盘大小除以20（18个格子+2个padding）
    const newCellSize = maxBoardSize / 20
    
    // 设置合理的格子大小范围
    const minCellSize = 12
    const maxCellSize = 40
    
    cellSize.value = Math.max(minCellSize, Math.min(maxCellSize, newCellSize))
    padding.value = cellSize.value
  }
}

onMounted(() => {
  // 延迟执行以确保DOM已渲染
  setTimeout(() => {
    updateBoardSize()
  }, 100)
  window.addEventListener('resize', updateBoardSize)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateBoardSize)
})

// 监听props变化时重新计算尺寸
watch(() => [props.board, props.moves], () => {
  setTimeout(() => {
    updateBoardSize()
  }, 50)
}, { deep: true })

// 事件监听已移至模板中的点击区域
</script>

<style scoped>
.weiqi-board-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  height: 120vh;
  min-height: 0;
  flex: 1;
}

.board-wrapper {
  background: #2a2a2a;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #444; 
  width: 100%;
  height: 100%;
  max-width: none;
  max-height: none;
  display: flex;
  justify-content: center;
  align-items: center;
}

.weiqi-board {
  cursor: crosshair;
}

.stone {
  filter: drop-shadow(0.2vh 0.2vh 0.4vh rgba(0, 0, 0, 0.3));
}

.last-move-marker {
  animation: fadeIn 0.5s ease;
}

.hover-stone {
  pointer-events: none;
}

.click-area {
  cursor: pointer;
  transition: opacity 0.2s;
}

.click-area:hover {
  opacity: 0.1;
  fill: #000;
}

.captured-stone {
  animation: captureAnimation 0.8s ease-out forwards;
  pointer-events: none;
}

@keyframes captureAnimation {
  0% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
  100% {
    opacity: 0;
    transform: scale(0.8);
  }
}

@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.5); }
  to { opacity: 1; transform: scale(1); }
}

.ai-suggestion {
  pointer-events: none;
}

.suggestion-number {
  pointer-events: none;
  user-select: none;
}

@media (max-width: 3840x) {
  .board-wrapper {
    padding: 1%;
  }
}
</style>