<template>
  <div class="move-history-chart">
    <div class="chart-header">
      <el-icon class="chart-icon"><TrendCharts /></el-icon>
      <span class="chart-title">胜率走势</span>
      <span class="move-count-text">第 {{ processedData.length }} 手</span>
      <!-- 滚动控制按钮 -->
      <div class="scroll-controls" v-if="showScrollControls">
        <button @click="scrollLeft" :disabled="scrollOffset === 0" class="scroll-btn">‹</button>
        <span class="scroll-info">{{ scrollOffset + 1 }}-{{ Math.min(scrollOffset + maxVisibleMoves, processedData.length) }}/{{ processedData.length }}</span>
        <button @click="scrollRight" :disabled="scrollOffset + maxVisibleMoves >= processedData.length" class="scroll-btn">›</button>
      </div>
    </div>
    <div class="chart-container" ref="chartContainer">
      <svg ref="svgChart" class="chart-svg"></svg>
      <!-- 悬浮提示框 -->
      <div ref="tooltip" class="tooltip" style="opacity: 0;">
        <svg class="pie-chart" width="50" height="50" viewBox="0 0 50 50">
          <g transform="translate(25,25)">
            <circle cx="0" cy="0" r="20" fill="none" stroke="#00ff88" stroke-width="1" opacity="0.3"></circle>
            <path :d="blackArc" fill="#333" stroke="#00ff88" stroke-width="1"></path>
            <path :d="whiteArc" fill="#ddd" stroke="#00ff88" stroke-width="1"></path>
            <text x="0" y="-6" text-anchor="middle" fill="#00ff88" font-size="7" font-weight="bold">{{ tooltipData.blackScore }}</text>
            <text x="0" y="6" text-anchor="middle" fill="#00ff88" font-size="7" font-weight="bold">{{ tooltipData.whiteScore }}</text>
          </g>
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed, nextTick } from 'vue'
import * as d3 from 'd3'
import { TrendCharts } from '@element-plus/icons-vue'

// Props
const props = defineProps({
  gameState: {
    type: Object,
    required: true
  },
  aiAnalysis: {
    type: Array,
    default: () => []
  },
  // 分支相关props已移除 - 使用简单回溯机制
})

// Emits
const emit = defineEmits(['go-to-move'])

// Refs
const chartContainer = ref(null)
const svgChart = ref(null)
const tooltip = ref(null)

// 数据
const tooltipData = ref({
  moveNumber: 0,
  moveColor: '',
  movePosition: '',
  winrate: 0,
  blackScore: 0,
  whiteScore: 0
})

// 滚动相关
const maxVisibleMoves = 10  // 最多显示15手
const scrollOffset = ref(0)  // 滚动偏移量

// 是否显示滚动控制
const showScrollControls = computed(() => {
  return processedData.value.length > maxVisibleMoves
})

// 当前显示的数据
const visibleData = computed(() => {
  if (processedData.value.length <= maxVisibleMoves) {
    return processedData.value
  }
  return processedData.value.slice(scrollOffset.value, scrollOffset.value + maxVisibleMoves)
})

// 滚动控制函数
const scrollLeft = () => {
  if (scrollOffset.value > 0) {
    scrollOffset.value = Math.max(0, scrollOffset.value - 5)
  }
}

const scrollRight = () => {
  const maxOffset = Math.max(0, processedData.value.length - maxVisibleMoves)
  if (scrollOffset.value < maxOffset) {
    scrollOffset.value = Math.min(maxOffset, scrollOffset.value + 5)
  }
}

// 重置组件状态
const resetChart = () => {
  scrollOffset.value = 0
  tooltipData.value = {
    moveNumber: 0,
    moveColor: '',
    movePosition: '',
    winrate: 0,
    blackScore: 0,
    whiteScore: 0
  }
  // 隐藏提示框
  if (tooltip.value) {
    tooltip.value.style.opacity = '0'
  }
}

// 自动滚动到最新手数
const autoScrollToLatest = () => {
  // 自动滚动到最新数据
  if (processedData.value.length > maxVisibleMoves) {
    scrollOffset.value = Math.max(0, processedData.value.length - maxVisibleMoves)
  }
}

// 滚动到指定手数
const scrollToMove = (moveNumber) => {
  if (processedData.value.length <= maxVisibleMoves) {
    return // 如果数据不多，不需要滚动
  }
  
  // 计算目标手数应该在的滚动位置
  const targetIndex = moveNumber - 1 // moveNumber是1-based，转换为0-based
  const targetOffset = Math.max(0, Math.min(
    targetIndex - Math.floor(maxVisibleMoves / 2), // 让目标手数显示在中间
    processedData.value.length - maxVisibleMoves
  ))
  
  scrollOffset.value = targetOffset
}

// 图表尺寸
const margin = { top: 20, right: 30, bottom: 40, left: 50 }
const width = 300
const height = 200
const innerWidth = width - margin.left - margin.right
const innerHeight = height - margin.top - margin.bottom

// 计算饼图弧度
const blackArc = computed(() => {
  const total = tooltipData.value.blackScore + tooltipData.value.whiteScore
  if (total === 0) return ''
  const angle = (tooltipData.value.blackScore / total) * 2 * Math.PI
  const arc = d3.arc()
    .innerRadius(0)
    .outerRadius(20)
    .startAngle(0)
    .endAngle(angle)
  return arc()
})

const whiteArc = computed(() => {
  const total = tooltipData.value.blackScore + tooltipData.value.whiteScore
  if (total === 0) return ''
  const blackAngle = (tooltipData.value.blackScore / total) * 2 * Math.PI
  const arc = d3.arc()
    .innerRadius(0)
    .outerRadius(20)
    .startAngle(blackAngle)
    .endAngle(2 * Math.PI)
  return arc()
})

// 处理历史数据
const processedData = computed(() => {
  if (!props.gameState.moves || props.gameState.moves.length === 0) {
    return []
  }
  
  // 使用真实的胜率历史数据
  const winrateHistory = props.gameState.winrate_history || []
  
  const mainData = props.gameState.moves.map((move, index) => {
    const [color, position] = move
    
    // 查找对应的胜率历史数据
    const historyData = winrateHistory.find(h => h.move_number === index + 1)
    
    let winrate, blackScore, whiteScore
    if (historyData) {
      // 使用真实数据 - 始终使用黑棋胜率
      winrate = historyData.black_winrate
      // 根据得分差计算目数（简化处理）
      const scoreLead = historyData.score_lead || 0
      if (color === 'B') {
        blackScore = Math.max(0, 50 + scoreLead)
        whiteScore = Math.max(0, 50 - scoreLead)
      } else {
        whiteScore = Math.max(0, 50 + scoreLead)
        blackScore = Math.max(0, 50 - scoreLead)
      }
    } else {
      // 如果没有历史数据，使用默认值
      winrate = 50
      blackScore = 50
      whiteScore = 50
    }
    
    return {
      moveNumber: index + 1,
      color: color,
      position: position === 'pass' ? '跳过' : position,
      winrate: Math.max(0, Math.min(100, winrate)),
      blackScore: Math.round(blackScore),
      whiteScore: Math.round(whiteScore),
      isBranch: false
    }
  })
  
  // 分支数据处理逻辑已移除 - 使用简单回溯机制
  
  return mainData
})



// 绘制图表
const drawChart = () => {
  if (!chartContainer.value || !svgChart.value || visibleData.value.length === 0) {
    return
  }
  
  // 清除之前的内容
  d3.select(svgChart.value).selectAll('*').remove()
  
  // 清除选中状态
  d3.select(svgChart.value).selectAll('.selected-point').remove()
  
  const svg = d3.select(svgChart.value)
    .attr('width', width)
    .attr('height', height)
  
  const g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)
  
  // 设置比例尺 - 使用可见数据的范围
  const xScale = d3.scaleLinear()
    .domain([visibleData.value[0]?.moveNumber || 1, visibleData.value[visibleData.value.length - 1]?.moveNumber || 1])
    .range([0, innerWidth])
  
  // Y轴：白棋胜率从顶部开始(100%白棋胜率在顶部，0%在底部)
  // 黑棋胜率从底部开始(100%黑棋胜率在底部，0%在顶部)
  const yScale = d3.scaleLinear()
    .domain([0, 100])  // 0%到100%
    .range([innerHeight, 0])  // 底部到顶部
  
  // 创建线条生成器
  const line = d3.line()
    .x(d => xScale(d.moveNumber))
    .y(d => {
      // winrate始终表示黑棋胜率
      // 黑棋胜率高时在底部，白棋胜率高时在顶部
      return yScale(100 - d.winrate)  // 反向显示：黑棋100%在底部，白棋100%在顶部
    })
    .curve(d3.curveMonotoneX)
  
  // 绘制网格线
  g.append('g')
    .attr('class', 'grid')
    .attr('transform', `translate(0,${innerHeight})`)
    .call(d3.axisBottom(xScale)
      .tickSize(-innerHeight)
      .tickFormat('')
    )
    .style('stroke-dasharray', '3,3')
    .style('opacity', 0.3)
  
  g.append('g')
    .attr('class', 'grid')
    .call(d3.axisLeft(yScale)
      .tickSize(-innerWidth)
      .tickFormat('')
    )
    .style('stroke-dasharray', '3,3')
    .style('opacity', 0.3)
  
  // 绘制坐标轴
  g.append('g')
    .attr('transform', `translate(0,${innerHeight})`)
    .call(d3.axisBottom(xScale).tickFormat(d => `${d}手`))
    .style('color', '#888')
  
  g.append('g')
    .call(d3.axisLeft(yScale).tickFormat(d => {
      // 自定义Y轴标签：顶部显示白棋胜率，底部显示黑棋胜率
      if (d === 100) return '白100%'
      if (d === 75) return '白75%'
      if (d === 50) return '50%'
      if (d === 25) return '黑75%'
      if (d === 0) return '黑100%'
      return `${d}%`
    }))
    .style('color', '#888')
  
  // 添加中线（50%胜率线）
  g.append('line')
    .attr('x1', 0)
    .attr('x2', innerWidth)
    .attr('y1', yScale(50))
    .attr('y2', yScale(50))
    .style('stroke', '#666')
    .style('stroke-width', 2)
    .style('stroke-dasharray', '5,5')
  
  // 使用所有可见数据绘制主线
  const mainLineData = visibleData.value
  
  // 绘制主胜率折线
  if (mainLineData.length > 0) {
    g.append('path')
      .datum(mainLineData)
      .attr('fill', 'none')
      .attr('stroke', '#00ff88')
      .attr('stroke-width', 2)
      .attr('d', line)
  }
  
  // 分支线渲染逻辑已移除 - 使用简单回溯机制
  
  // 绘制数据点
  const circles = g.selectAll('.data-point')
    .data(visibleData.value)
    .enter().append('circle')
    .attr('class', 'data-point')
    .attr('cx', d => xScale(d.moveNumber))
    .attr('cy', d => {
      // winrate始终表示黑棋胜率
      // 黑棋胜率高时在底部，白棋胜率高时在顶部
      return yScale(100 - d.winrate)  // 反向显示：黑棋100%在底部，白棋100%在顶部
    })
    .attr('r', 4)
    .attr('fill', d => d.color === 'B' ? '#333' : '#ddd')
    .attr('stroke', '#00ff88')
    .attr('stroke-width', 2)
    .style('cursor', 'pointer')
  
  // 添加落子位置标注
  g.selectAll('.move-label')
    .data(visibleData.value)
    .enter().append('text')
    .attr('class', 'move-label')
    .attr('x', d => xScale(d.moveNumber))
    .attr('y', d => {
      // 标签位置跟随数据点
      // winrate始终表示黑棋胜率
      const yPos = yScale(100 - d.winrate)  // 反向显示：黑棋100%在底部，白棋100%在顶部
      return yPos - 10  // 标签在数据点上方10px
    })
    .attr('text-anchor', 'middle')
    .style('font-size', '10px')
    .style('fill', '#ccc')
    .text(d => d.position)
  
  // 添加交互事件
  circles
    .on('mouseover', function(event, d) {
      // 更新提示框数据
      tooltipData.value = {
        moveNumber: d.moveNumber,
        moveColor: d.color === 'B' ? '●' : '○',
        movePosition: d.position,
        winrate: Math.round(d.winrate),
        blackScore: d.blackScore,
        whiteScore: d.whiteScore
      }
      
      // 显示提示框
      const tooltipEl = d3.select(tooltip.value)
      tooltipEl.transition().duration(200).style('opacity', 1)
      
      // 定位提示框到数据点右上方
      const pointX = xScale(d.moveNumber)
      const pointY = yScale(100 - d.winrate)
      tooltipEl
        .style('left', (pointX + 10) + 'px')  // 右上方偏移
        .style('top', (pointY - 55) + 'px')
      
      // 高亮当前点
      d3.select(this)
        .transition().duration(100)
        .attr('r', 5)
        .attr('stroke-width', 3)
    })
    .on('mouseout', function() {
      // 隐藏提示框
      d3.select(tooltip.value)
        .transition().duration(200)
        .style('opacity', 0)
      
      // 恢复点的样式
      d3.select(this)
        .transition().duration(100)
        .attr('r', 4)
        .attr('stroke-width', 2)
    })
    .on('click', function(event, d) {
      // 清除之前的选中状态
      g.selectAll('.selected-point').remove()
      
      // 添加橙色圈住效果
      g.append('circle')
        .attr('class', 'selected-point')
        .attr('cx', xScale(d.moveNumber))
        .attr('cy', yScale(100 - d.winrate))
        .attr('r', 8)
        .attr('fill', 'none')
        .attr('stroke', '#ff8800')
        .attr('stroke-width', 3)
        .datum(d)
      
      // 点击回溯
      emit('go-to-move', d.moveNumber - 1)
    })
}

// 监听数据变化
watch(() => processedData.value, (newData, oldData) => {
  // 如果数据长度减少了，说明是回溯操作，不自动滚动到最新
  if (oldData && newData.length < oldData.length) {
    // 回溯时，确保滚动位置不超出新的数据范围
    const maxOffset = Math.max(0, newData.length - maxVisibleMoves)
    if (scrollOffset.value > maxOffset) {
      scrollOffset.value = maxOffset
    }
  } else {
    // 正常添加新手数时，自动滚动到最新
    autoScrollToLatest()
  }
}, { deep: true })

// 监听可见数据变化，重新绘制图表
watch(() => visibleData.value, () => {
  nextTick(() => {
    drawChart()
  })
}, { deep: true })

// 组件挂载后绘制图表
onMounted(() => {
  nextTick(() => {
    drawChart()
  })
})

// 暴露方法给父组件
defineExpose({
  resetChart,
  scrollToMove
})
</script>

<style scoped>
.move-history-chart {
  margin-bottom: 8px;
}

.chart-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.chart-icon {
  color: #00ff88;
  scale: 1.1;
}

.chart-title {
  font-size: 14px;
  color: #00ff88;
  font-weight: 600;
}

.move-count-text {
  font-size: 12px;
  color: #888;
  margin-left: auto;
}

.scroll-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.scroll-btn {
  background: #333;
  border: 1px solid #555;
  color: #ccc;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.scroll-btn:hover {
  background: #444;
  border-color: #00ff88;
  color: #00ff88;
}

.scroll-btn:disabled {
  background: #222;
  border-color: #333;
  color: #555;
  cursor: not-allowed;
}

.scroll-info {
  font-size: 11px;
  color: #888;
  white-space: nowrap;
}

.chart-container {
  position: relative;
  background: #1a1a1a;
  border-radius: 4px;
  padding: 8px;
}

.chart-svg {
  display: block;
  margin: 0 auto;
}

.tooltip {
  position: absolute;
  background: transparent;
  border: none;
  padding: 0;
  pointer-events: none;
  z-index: 1000;
}

.pie-chart {
  display: block;
}

/* D3 样式覆盖 */
:deep(.grid line) {
  stroke: #444;
}

:deep(.domain) {
  stroke: #666;
}

:deep(.tick text) {
  fill: #888;
  font-size: 10px;
}
</style>