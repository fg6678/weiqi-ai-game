const { app, BrowserWindow, Menu } = require('electron')
const path = require('path')
const isDev = process.env.NODE_ENV === 'development'

function createWindow() {
  // 创建浏览器窗口
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 1000,
    minHeight: 700,
    maxWidth: 1200,
    maxHeight: 800,
    resizable: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      webSecurity: true
    },
    icon: path.join(__dirname, '../public/favicon.ico'),
    title: 'Go AI Analysis System',
    show: false // 先不显示，等页面加载完成后再显示
  })

  // 页面加载完成后显示窗口
  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
    if (isDev) {
      mainWindow.webContents.openDevTools()
    }
  })

  // 加载应用
  if (isDev) {
    // 开发环境：连接到Vite开发服务器
    mainWindow.loadURL('http://localhost:5173')
  } else {
    // 生产环境：加载构建后的文件
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  // 窗口关闭时的处理
  mainWindow.on('closed', () => {
    // 在macOS上，应用通常会保持活跃状态
    // 即使没有打开的窗口，直到用户明确退出
    if (process.platform !== 'darwin') {
      app.quit()
    }
  })
}

// 当Electron完成初始化并准备创建浏览器窗口时调用此方法
app.whenReady().then(() => {
  createWindow()

  // 在macOS上，当点击dock图标并且没有其他窗口打开时，
  // 通常会重新创建一个窗口
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

// 当所有窗口都关闭时退出应用
app.on('window-all-closed', () => {
  // 在macOS上，应用和菜单栏通常会保持活跃状态
  // 直到用户明确退出
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// 在开发环境中，当主进程准备就绪时设置菜单
if (isDev) {
  app.whenReady().then(() => {
    // 开发环境菜单
    const template = [
      {
        label: '开发',
        submenu: [
          {
            label: '重新加载',
            accelerator: 'CmdOrCtrl+R',
            click: () => {
              BrowserWindow.getFocusedWindow()?.reload()
            }
          },
          {
            label: '强制重新加载',
            accelerator: 'CmdOrCtrl+Shift+R',
            click: () => {
              BrowserWindow.getFocusedWindow()?.webContents.reloadIgnoringCache()
            }
          },
          {
            label: '开发者工具',
            accelerator: 'F12',
            click: () => {
              BrowserWindow.getFocusedWindow()?.webContents.toggleDevTools()
            }
          }
        ]
      }
    ]
    
    const menu = Menu.buildFromTemplate(template)
    Menu.setApplicationMenu(menu)
  })
}