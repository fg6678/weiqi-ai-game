# AI模型502错误解决方案

## 问题描述
当使用代理（梯子）时，AI讲棋功能可能出现502错误，这是因为代理干扰了对本地ollama服务的连接。

## 解决方案

### 方案1: 设置代理排除规则（推荐）

在启动后端服务器前，设置环境变量排除本地地址：

```bash
export NO_PROXY='localhost,127.0.0.1,::1,0.0.0.0'
export no_proxy='localhost,127.0.0.1,::1,0.0.0.0'
python backend.py
```

### 方案2: 临时关闭代理

在启动后端服务器的终端中临时关闭代理：

```bash
export HTTP_PROXY=''
export HTTPS_PROXY=''
export http_proxy=''
export https_proxy=''
python backend.py
```

### 方案3: 在代理软件中设置排除规则

#### Clash
1. 打开Clash配置文件
2. 在rules部分添加：
```yaml
rules:
  - DOMAIN,localhost,DIRECT
  - IP-CIDR,127.0.0.0/8,DIRECT
  - IP-CIDR6,::1/128,DIRECT
```

#### V2Ray
1. 在路由设置中添加直连规则
2. 域名：localhost
3. IP：127.0.0.1/8, ::1/128

### 方案4: 系统代理设置（macOS）

1. 打开 **系统偏好设置** > **网络**
2. 选择当前网络连接，点击 **高级**
3. 切换到 **代理** 标签页
4. 在 **忽略这些主机与域的代理设置** 中添加：
   ```
   localhost
   127.0.0.1
   ::1
   *.local
   ```

## 自动诊断工具

运行诊断脚本来检查和修复代理问题：

```bash
python fix_proxy.py
```

这个脚本会：
- 检查ollama服务状态
- 显示当前代理设置
- 提供快速修复选项
- 给出详细的解决方案

## 验证修复

1. 重启后端服务器
2. 在前端尝试使用AI讲棋功能
3. 如果仍有问题，检查终端输出是否还有502错误

## 技术原理

问题的根本原因是：
- 代理软件拦截了所有HTTP/HTTPS请求
- 包括对localhost:11434（ollama服务）的请求
- 导致连接失败，返回502错误

解决方案通过以下方式绕过代理：
1. 设置NO_PROXY环境变量
2. 在代码中临时移除代理设置
3. 使用不带代理的httpx客户端

## 常见问题

**Q: 为什么不能直接关闭代理？**
A: 关闭代理可能影响其他需要代理的网络访问，设置排除规则是更好的选择。

**Q: 设置后仍然有502错误怎么办？**
A: 检查ollama服务是否正常运行，可以访问 http://localhost:11434/api/tags 测试。

**Q: 每次都要设置环境变量吗？**
A: 可以将环境变量设置添加到shell配置文件（如.bashrc, .zshrc）中永久生效。