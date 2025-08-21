# 围棋人机对弈系统

一个基于 FastAPI + Vue 3 + KataGo 的围棋人机对弈Web应用。

## 功能特性

- 🎯 实时围棋对弈界面
- 🤖 集成 KataGo AI 引擎
- 📱 响应式设计，支持移动端
- 🔄 WebSocket 实时通信
- 📊 AI 推荐着法显示
- 📝 着法历史记录

## 系统要求

- Python 3.8+
- Node.js 16+
- KataGo 引擎

## 安装和运行

### 1. 安装 Python 依赖

```bash
# 激活虚拟环境（如果有的话）
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 安装前端依赖

```bash
cd weiqi-web
npm install
```

### 3. 启动后端服务

```bash
# 在项目根目录
python backend.py
```

后端服务将在 `http://localhost:8000` 启动

### 4. 启动前端开发服务器

```bash
# 在 weiqi-web 目录
npm run dev
```

前端服务将在 `http://localhost:3000` 启动

## 使用说明

1. 打开浏览器访问 `http://localhost:3000`
2. 你执黑棋先行，可以通过以下方式下棋：
   - 直接点击棋盘上的交叉点
   - 在输入框中输入坐标（如：D4, Q16）
   - 输入 "pass" 选择过
3. KataGo 会自动应对你的着法
4. 查看右侧面板的 AI 推荐着法和着法历史

## 项目结构

```
.
├── backend.py              # FastAPI 后端服务
├── human_vs_katago.py      # 原始命令行版本
├── requirements.txt        # Python 依赖
├── analysis.cfg           # KataGo 配置文件
└── weiqi-web/             # Vue 前端项目
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.js
        ├── App.vue
        ├── style.css
        └── components/
            ├── WeiQiBoard.vue
            ├── GameInfo.vue
            └── MovesHistory.vue
```

## 技术栈

### 后端
- **FastAPI**: 现代、快速的 Web 框架
- **WebSocket**: 实时双向通信
- **KataGo**: 世界级围棋 AI 引擎

### 前端
- **Vue 3**: 渐进式 JavaScript 框架
- **Vite**: 快速的前端构建工具
- **CSS Grid**: 响应式布局

## 配置说明

确保以下文件路径正确：
- KataGo 模型文件：`/Volumes/exdata/katago/models/kata1-b28c512nbt-s10063600896-d5087116207.bin.gz`
- KataGo 配置文件：`/Volumes/exdata/projects/weiqitest/analysis.cfg`

如需修改路径，请编辑 `backend.py` 文件中的 `MODEL` 和 `CFG` 变量。

## 故障排除

1. **KataGo 启动失败**：检查模型文件和配置文件路径是否正确
2. **WebSocket 连接失败**：确保后端服务正在运行
3. **前端无法访问**：检查端口是否被占用

## 许可证

MIT License