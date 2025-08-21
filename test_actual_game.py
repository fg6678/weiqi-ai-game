#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试实际游戏落子和数据存储
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.human_vs_katago import WeiQiGame
from core.analysis_game import AnalysisGame
import time

def test_human_vs_ai_game():
    """测试Human vs AI模式的数据存储"""
    print("=== 测试Human vs AI模式数据存储 ===")
    
    try:
        # 创建游戏实例
        game = WeiQiGame()
        print(f"✅ 游戏创建成功，游戏ID: {game.evolution_storage.game_id}")
        
        # 模拟几步棋
        moves = ["D4", "Q16", "D16", "Q4", "C3"]
        
        for i, move in enumerate(moves, 1):
            print(f"\n--- 第{i}步: {move} ---")
            
            # 落子
            success = game.make_move(move)
            if success:
                print(f"✅ 落子成功: {move}")
                
                # 等待数据处理完成
                time.sleep(1)
                
                # 检查胜率历史
                if game.winrate_history:
                    latest_wr = game.winrate_history[-1]
                    print(f"📊 胜率数据: 黑{latest_wr.get('black_winrate', 0):.1f}% 白{latest_wr.get('white_winrate', 0):.1f}%")
                else:
                    print("⚠️ 无胜率数据")
                
            else:
                print(f"❌ 落子失败: {move}")
                break
        
        # 检查MongoDB中的数据
        print("\n=== 检查MongoDB数据 ===")
        evolution_data = game.evolution_storage.get_evolution_data()
        print(f"📋 演化数据条目: {len(evolution_data)}")
        
        for data in evolution_data:
            move_num = data.get('move_number', 0)
            move = data.get('move', 'N/A')
            color = data.get('color', 'N/A')
            
            winrate_data = data.get('winrate_data', {})
            black_wr = winrate_data.get('black_winrate', 0)
            white_wr = winrate_data.get('white_winrate', 0)
            
            recommended = data.get('recommended_moves', [])
            territory = data.get('territory_prediction', {})
            
            print(f"  步骤{move_num}: {move} ({color}) - 黑{black_wr}% 白{white_wr}% - 推荐{len(recommended)}个 - 领地{len(territory.get('black_territory', []))}+{len(territory.get('white_territory', []))}")
        
        # 清理
        game.cleanup()
        print("\n✅ Human vs AI测试完成")
        
    except Exception as e:
        print(f"❌ Human vs AI测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_analysis_game():
    """测试推演模式的数据存储"""
    print("\n=== 测试推演模式数据存储 ===")
    
    try:
        # 创建推演游戏实例
        game = AnalysisGame()
        print(f"✅ 推演游戏创建成功，游戏ID: {game.evolution_storage.game_id}")
        
        # 模拟几步棋
        moves = ["D4", "Q16", "D16"]
        
        for i, move in enumerate(moves, 1):
            print(f"\n--- 推演第{i}步: {move} ---")
            
            # 落子
            success = game.make_move(move)
            if success:
                print(f"✅ 推演落子成功: {move}")
                
                # 等待数据处理完成
                time.sleep(1)
                
                # 检查胜率历史
                if game.winrate_history:
                    latest_wr = game.winrate_history[-1]
                    black_wr = latest_wr.get('black_winrate', latest_wr.get('winrate', 0) * 100)
                    print(f"📊 推演胜率数据: 黑{black_wr:.1f}%")
                else:
                    print("⚠️ 无推演胜率数据")
                
            else:
                print(f"❌ 推演落子失败: {move}")
                break
        
        # 检查MongoDB中的数据
        print("\n=== 检查推演MongoDB数据 ===")
        evolution_data = game.evolution_storage.get_evolution_data()
        print(f"📋 推演演化数据条目: {len(evolution_data)}")
        
        for data in evolution_data:
            move_num = data.get('move_number', 0)
            move = data.get('move', 'N/A')
            color = data.get('color', 'N/A')
            
            winrate_data = data.get('winrate_data', {})
            black_wr = winrate_data.get('black_winrate', 0)
            white_wr = winrate_data.get('white_winrate', 0)
            
            recommended = data.get('recommended_moves', [])
            territory = data.get('territory_prediction', {})
            
            print(f"  推演步骤{move_num}: {move} ({color}) - 黑{black_wr}% 白{white_wr}% - 推荐{len(recommended)}个 - 领地{len(territory.get('black_territory', []))}+{len(territory.get('white_territory', []))}")
        
        # 清理
        game.cleanup()
        print("\n✅ 推演模式测试完成")
        
    except Exception as e:
        print(f"❌ 推演模式测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 测试Human vs AI模式
    test_human_vs_ai_game()
    
    # 测试推演模式
    test_analysis_game()
    
    print("\n=== 所有测试完成 ===")