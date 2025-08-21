#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试MongoDB数据脚本
查看当前数据库中的实际数据情况
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from storage.game_evolution_mongodb import GameEvolutionMongoDB
from storage.mongodb_config import mongo_config
import json
from datetime import datetime

def debug_current_games():
    """调试当前游戏数据"""
    print("=== 调试MongoDB当前数据 ===")
    
    try:
        # 获取最近的游戏列表
        games = GameEvolutionMongoDB.list_games(limit=5)
        
        if not games:
            print("❌ 没有找到任何游戏数据")
            return
        
        print(f"📋 找到 {len(games)} 个游戏:")
        for i, game in enumerate(games, 1):
            print(f"\n{i}. 游戏ID: {game.get('game_id')}")
            print(f"   状态: {game.get('game_status')}")
            print(f"   总步数: {game.get('total_moves')}")
            print(f"   创建时间: {game.get('created_at')}")
            print(f"   更新时间: {game.get('updated_at')}")
            
            # 获取详细数据
            storage = GameEvolutionMongoDB(game.get('game_id'))
            evolution_data = storage.get_evolution_data()
            
            print(f"   演化数据条目: {len(evolution_data)}")
            
            # 检查最近几步的数据质量
            if evolution_data:
                print("   最近步骤数据质量检查:")
                for j, move_data in enumerate(evolution_data[-3:], 1):  # 检查最后3步
                    move_num = move_data.get('move_number', 0)
                    move = move_data.get('move', 'N/A')
                    color = move_data.get('color', 'N/A')
                    
                    print(f"     步骤{move_num}: {move} ({color})")
                    
                    # 检查胜率数据
                    winrate_data = move_data.get('winrate_data', {})
                    black_wr = winrate_data.get('black_winrate', 0)
                    white_wr = winrate_data.get('white_winrate', 0)
                    score_lead = winrate_data.get('score_lead', 0)
                    print(f"       胜率: 黑{black_wr}% 白{white_wr}% 目差{score_lead}")
                    
                    # 检查推荐着法
                    recommended = move_data.get('recommended_moves', [])
                    print(f"       推荐着法: {len(recommended)}个")
                    if recommended:
                        best_move = recommended[0]
                        print(f"         最佳: {best_move.get('move', 'N/A')} (胜率{best_move.get('winrate', 0)*100:.1f}%)")
                    
                    # 检查领地数据
                    territory = move_data.get('territory_prediction', {})
                    black_territory = len(territory.get('black_territory', []))
                    white_territory = len(territory.get('white_territory', []))
                    neutral_points = len(territory.get('neutral_points', []))
                    print(f"       领地: 黑{black_territory}点 白{white_territory}点 中性{neutral_points}点")
                    
                    # 检查棋块数据
                    stone_groups = move_data.get('stone_groups', [])
                    print(f"       棋块: {len(stone_groups)}个")
                    
                    # 检查已落子数据
                    placed_stones = move_data.get('placed_stones', [])
                    print(f"       已落子: {len(placed_stones)}个")
                    
                    # 数据质量评估
                    issues = []
                    if black_wr == 50.0 and white_wr == 50.0 and score_lead == 0.0:
                        issues.append("胜率数据为默认值")
                    if len(recommended) == 0:
                        issues.append("无推荐着法")
                    if black_territory == 0 and white_territory == 0 and neutral_points == 0:
                        issues.append("无领地数据")
                    if len(stone_groups) == 0 and len(placed_stones) > 0:
                        issues.append("棋块分析缺失")
                    
                    if issues:
                        print(f"       ⚠️ 数据问题: {', '.join(issues)}")
                    else:
                        print(f"       ✅ 数据完整")
            
            print("-" * 50)
    
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()

def debug_specific_game(game_id: str):
    """调试特定游戏的详细数据"""
    print(f"\n=== 调试游戏 {game_id} 的详细数据 ===")
    
    try:
        storage = GameEvolutionMongoDB(game_id)
        game_data = storage.get_game_data()
        
        if not game_data:
            print(f"❌ 游戏 {game_id} 不存在")
            return
        
        print(f"📊 游戏基本信息:")
        print(f"   ID: {game_data.get('game_id')}")
        print(f"   状态: {game_data.get('game_status')}")
        print(f"   总步数: {game_data.get('total_moves')}")
        print(f"   玩家: {game_data.get('players')}")
        
        evolution_data = game_data.get('evolution_data', [])
        print(f"\n📈 演化数据详情 ({len(evolution_data)} 条):")
        
        for i, move_data in enumerate(evolution_data):
            print(f"\n步骤 {i+1}:")
            print(f"  原始数据: {json.dumps(move_data, indent=2, default=str, ensure_ascii=False)}")
    
    except Exception as e:
        print(f"❌ 调试特定游戏失败: {e}")
        import traceback
        traceback.print_exc()

def check_mongodb_connection():
    """检查MongoDB连接状态"""
    print("=== 检查MongoDB连接 ===")
    
    try:
        if mongo_config.connect():
            print("✅ MongoDB连接正常")
            print(f"📍 连接地址: {mongo_config.connection_string}")
            print(f"🗄️ 数据库: {mongo_config.database_name}")
            return True
        else:
            print("❌ MongoDB连接失败")
            return False
    except Exception as e:
        print(f"❌ MongoDB连接异常: {e}")
        return False

if __name__ == "__main__":
    # 检查连接
    if not check_mongodb_connection():
        print("无法连接到MongoDB，退出调试")
        sys.exit(1)
    
    # 调试当前游戏数据
    debug_current_games()
    
    # 如果用户提供了特定游戏ID，调试该游戏
    if len(sys.argv) > 1:
        game_id = sys.argv[1]
        debug_specific_game(game_id)