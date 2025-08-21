#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试AI讲棋模块获取MongoDB最近记录功能
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai.ai_handler import AIHandler
from core.human_vs_katago import WeiQiGame
from storage.game_evolution_mongodb import GameEvolutionMongoDB

async def test_ai_commentary_with_mongodb():
    """测试AI讲棋功能获取MongoDB数据"""
    print("=== 测试AI讲棋模块获取MongoDB最近记录 ===")
    
    try:
        # 1. 创建一个测试游戏并添加一些数据
        print("\n1. 创建测试游戏并添加数据...")
        test_game_id = "test_ai_commentary_game"
        storage = GameEvolutionMongoDB(test_game_id)
        
        # 添加一些测试数据
        test_moves = [
            {"move_number": 1, "move": "D4", "color": "B", 
             "winrate_data": {"black_winrate": 0.52, "white_winrate": 0.48},
             "recommended_moves": [{"move": "Q16", "winrate": 0.53}, {"move": "D16", "winrate": 0.51}]},
            {"move_number": 2, "move": "Q16", "color": "W", 
             "winrate_data": {"black_winrate": 0.49, "white_winrate": 0.51},
             "recommended_moves": [{"move": "D16", "winrate": 0.52}, {"move": "Q4", "winrate": 0.50}]},
            {"move_number": 3, "move": "D16", "color": "B", 
             "winrate_data": {"black_winrate": 0.53, "white_winrate": 0.47},
             "recommended_moves": [{"move": "Q4", "winrate": 0.54}, {"move": "C3", "winrate": 0.52}]}
        ]
        
        for move_data in test_moves:
            storage.add_move_data(
                move_data["move_number"],
                move_data["move"],
                move_data["color"],
                move_data["winrate_data"],
                recommended_moves=move_data["recommended_moves"]
            )
        
        print(f"✅ 测试数据添加完成，游戏ID: {test_game_id}")
        
        # 2. 创建一个模拟游戏对象
        print("\n2. 创建模拟游戏对象...")
        game = WeiQiGame()
        game.evolution_storage = storage  # 设置演化存储
        
        # 3. 创建AI处理器并测试用户问题回答
        print("\n3. 测试AI讲棋功能...")
        ai_handler = AIHandler()
        
        # 测试问题列表
        test_questions = [
            "当前局面黑棋的胜率如何？",
            "AI推荐的下一步着法是什么？",
            "这个开局的特点是什么？"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n--- 测试问题 {i}: {question} ---")
            try:
                response = await ai_handler.generate_user_response(game, question)
                print(f"AI回答: {response}")
            except Exception as e:
                print(f"❌ 回答问题失败: {e}")
        
        # 4. 测试获取最近游戏列表的情况
        print("\n4. 测试获取最近游戏列表...")
        game_without_storage = WeiQiGame()  # 没有evolution_storage的游戏
        try:
            response = await ai_handler.generate_user_response(game_without_storage, "最近有什么有趣的对局？")
            print(f"AI回答（无当前游戏数据）: {response}")
        except Exception as e:
            print(f"❌ 回答问题失败: {e}")
        
        print("\n=== 测试完成 ===")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_commentary_with_mongodb())