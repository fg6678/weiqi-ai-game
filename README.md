# 围棋AI对弈系统 (Weiqi AI Game)

一个功能完整的围棋AI对弈系统，支持人机对战、AI讲棋和棋局分析功能。

## 🎯 主要功能

### 🤖 人机对战
- 集成KataGo引擎，提供强大的AI对手
- 支持多种难度级别调整
- 实时棋局状态显示和胜率分析

### 🎙️ AI讲棋
- 支持多种大语言模型（Ollama）
- 动态模型选择（Qwen3、Gemma3等）
- 实时棋局解说和策略分析
- 智能落子建议和局面评估

### 📊 棋局分析
- 完整的对局记录和回放
- 胜率变化曲线图
- 关键手分析和复盘功能
- MongoDB数据持久化存储

## 🏗️ 技术架构

### 后端技术栈
- **Python 3.8+** - 核心开发语言
- **FastAPI** - 高性能Web框架
- **WebSocket** - 实时通信
- **MongoDB** - 数据存储
- **KataGo** - 围棋AI引擎
- **Ollama** - 大语言模型服务

### 前端技术栈
- **Vue 3** - 渐进式JavaScript框架
- **TypeScript** - 类型安全
- **Element Plus** - UI组件库
- **Vite** - 构建工具
- **Pinia** - 状态管理

## 📁 项目结构

```
weiqi-ai-game/
├── ai/                    # AI相关模块
│   ├── ai_handler.py     # AI讲棋处理器
│   └── __init__.py
├── api/                   # API接口层
│   ├── backend.py        # FastAPI后端服务
│   └── __init__.py
├── core/                  # 核心游戏逻辑
│   ├── analysis_game.py  # 棋局分析
│   ├── human_vs_katago.py # 人机对战
│   └── __init__.py
├── storage/               # 数据存储层
│   ├── game_evolution_mongodb.py # MongoDB存储
│   ├── mongodb_config.py # 数据库配置
│   ├── mongodb_schema.py # 数据模型
│   └── __init__.py
├── utils/                 # 工具模块
│   ├── katagott.py       # KataGo工具
│   ├── fix_proxy.py      # 代理修复
│   └── __init__.py
├── weiqi-web/            # Vue前端项目
│   ├── src/
│   │   ├── components/   # 组件
│   │   ├── views/        # 页面
│   │   └── stores/       # 状态管理
│   └── package.json
├── tests/                # 测试文件
├── requirements.txt      # Python依赖
└── README.md            # 项目说明
```

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- MongoDB 4.4+
- KataGo引擎
- Ollama服务

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/fg6678/weiqi-ai-game.git
cd weiqi-ai-game
```

2. **安装Python依赖**
```bash
pip install -r requirements.txt
```

3. **安装前端依赖**
```bash
cd weiqi-web
npm install
```

4. **配置环境**
- 安装并启动MongoDB
- 安装并配置KataGo
- 安装并启动Ollama服务

5. **启动服务**

后端服务：
```bash
python api/backend.py
```

前端服务：
```bash
cd weiqi-web
npm run dev
```

6. **访问应用**
打开浏览器访问 `http://localhost:5173`

## 🎮 使用说明

### 人机对战模式
1. 选择"人机对战"模式
2. 设置AI难度级别
3. 开始对局，点击棋盘落子
4. 查看实时胜率分析

### AI讲棋模式
1. 选择"AI讲棋"模式
2. 从下拉列表选择AI模型
3. 开始对局，AI将实时解说
4. 查看AI的策略分析和建议

### 棋局分析
1. 在对局结束后自动保存
2. 查看完整的对局记录
3. 分析胜率变化曲线
4. 复盘关键手和转折点

## 🔧 配置说明

### MongoDB配置
在 `storage/mongodb_config.py` 中配置数据库连接：
```python
MONGO_URL = "mongodb://localhost:27017"
DATABASE_NAME = "weiqi_game"
```

### KataGo配置
确保KataGo引擎路径正确配置在相关模块中。

### Ollama模型
支持的模型包括：
- qwen3:4b-instruct
- gemma3:2b
- llama3:8b
- 其他Ollama支持的模型

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [KataGo](https://github.com/lightvector/KataGo) - 强大的围棋AI引擎
- [Ollama](https://ollama.ai/) - 本地大语言模型服务
- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
- [FastAPI](https://fastapi.tiangolo.com/) - 现代Python Web框架

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- GitHub Issues: [提交问题](https://github.com/fg6678/weiqi-ai-game/issues)
- Email: [你的邮箱]

---

⭐ 如果这个项目对你有帮助，请给个Star支持一下！