#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理问题修复脚本

这个脚本提供了几种解决AI模型调用502错误的方法：
1. 临时关闭代理环境变量
2. 设置代理排除规则
3. 检查ollama服务状态
"""

import os
import subprocess
import sys

def check_ollama_status():
    """检查ollama服务状态"""
    try:
        result = subprocess.run(['curl', '-s', 'http://localhost:11434/api/tags'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Ollama服务运行正常")
            return True
        else:
            print("❌ Ollama服务未响应")
            return False
    except Exception as e:
        print(f"❌ 检查Ollama服务失败: {e}")
        return False

def show_proxy_status():
    """显示当前代理设置"""
    print("\n当前代理设置:")
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']
    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            print(f"  {var}: {value}")
        else:
            print(f"  {var}: 未设置")

def set_no_proxy():
    """设置NO_PROXY环境变量排除本地地址"""
    current_no_proxy = os.environ.get('NO_PROXY', '')
    localhost_addresses = 'localhost,127.0.0.1,::1,0.0.0.0'
    
    if current_no_proxy:
        # 检查是否已经包含本地地址
        if 'localhost' not in current_no_proxy or '127.0.0.1' not in current_no_proxy:
            new_no_proxy = f"{current_no_proxy},{localhost_addresses}"
        else:
            new_no_proxy = current_no_proxy
    else:
        new_no_proxy = localhost_addresses
    
    os.environ['NO_PROXY'] = new_no_proxy
    os.environ['no_proxy'] = new_no_proxy
    
    print(f"\n✅ 已设置NO_PROXY: {new_no_proxy}")
    print("这将排除本地地址使用代理")

def clear_proxy_env():
    """临时清除代理环境变量"""
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    cleared = []
    
    for var in proxy_vars:
        if var in os.environ:
            del os.environ[var]
            cleared.append(var)
    
    if cleared:
        print(f"\n✅ 已临时清除代理变量: {', '.join(cleared)}")
        print("注意: 这只在当前Python进程中有效")
    else:
        print("\n📝 没有发现需要清除的代理变量")

def show_solutions():
    """显示解决方案"""
    print("\n🔧 解决AI模型502错误的方法:")
    print("\n方法1: 在终端中临时关闭代理 (推荐)")
    print("  export HTTP_PROXY=''")
    print("  export HTTPS_PROXY=''")
    print("  export http_proxy=''")
    print("  export https_proxy=''")
    print("  python backend.py")
    
    print("\n方法2: 设置代理排除规则")
    print("  export NO_PROXY='localhost,127.0.0.1,::1,0.0.0.0'")
    print("  export no_proxy='localhost,127.0.0.1,::1,0.0.0.0'")
    
    print("\n方法3: 在代理软件中添加排除规则")
    print("  - 在Clash/V2Ray等代理软件中")
    print("  - 添加规则排除 localhost 和 127.0.0.1")
    print("  - 或者设置直连模式处理本地地址")
    
    print("\n方法4: 使用系统代理设置")
    print("  macOS: 系统偏好设置 > 网络 > 高级 > 代理")
    print("  在'忽略这些主机与域的代理设置'中添加:")
    print("  localhost, 127.0.0.1, ::1")

def main():
    print("🔍 AI模型代理问题诊断工具")
    print("=" * 40)
    
    # 检查ollama状态
    ollama_ok = check_ollama_status()
    
    # 显示当前代理状态
    show_proxy_status()
    
    if not ollama_ok:
        print("\n⚠️  请先确保Ollama服务正在运行:")
        print("   ollama serve")
        print("   或者检查Ollama是否已安装并正确配置")
        return
    
    # 显示解决方案
    show_solutions()
    
    print("\n🚀 快速修复选项:")
    print("1. 设置NO_PROXY排除本地地址")
    print("2. 临时清除代理环境变量")
    print("3. 仅显示解决方案")
    print("4. 退出")
    
    try:
        choice = input("\n请选择 (1-4): ").strip()
        
        if choice == '1':
            set_no_proxy()
            print("\n💡 建议重启后端服务器以应用更改")
        elif choice == '2':
            clear_proxy_env()
            print("\n💡 请在同一终端窗口中重启后端服务器")
        elif choice == '3':
            pass  # 解决方案已经显示过了
        elif choice == '4':
            print("\n👋 退出")
            return
        else:
            print("\n❌ 无效选择")
            
    except KeyboardInterrupt:
        print("\n\n👋 退出")

if __name__ == "__main__":
    main()