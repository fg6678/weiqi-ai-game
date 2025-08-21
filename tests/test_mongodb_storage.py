#!/usr/bin/env python3
"""
MongoDB存储功能测试脚本
"""

import sys
import os
from datetime import datetime
from storage.game_evolution_mongodb import GameEvolutionMongoDB
from storage.mongodb_config import mongo_config

def test_mongodb_connection():
    """测试MongoDB连接"""
    print("🔍 测试MongoDB连接...")
    try:
        if mongo_config.connect():
            print("✅ MongoDB连接测试成功")
            return True
        else:
            print("❌ MongoDB连接测试失败")
            return False
    except Exception as e:
        print(f"❌ MongoDB连接异常: {e}")
        return False

def test_game_creation():
    """测试游戏创建"""
    print("\n🎮 测试游戏创建...")
    try:
        # 创建测试游戏
        test_game_id = f"test_mongodb_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        storage = GameEvolutionMongoDB(test_game_id)
        
        # 获取游戏数据
        game_data = storage.get_game_data()
        if game_data:
            print(f"✅ 游戏创建成功: {test_game_id}")
            print(f"📊 游戏状态: {game_data.get('game_status')}")
            print(f"📅 创建时间: {game_data.get('created_at')}")
            return storage, test_game_id
        else:
            print("❌ 游戏创建失败")
            return None, None
    except Exception as e:
        print(f"❌ 游戏创建异常: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def test_move_data_storage(storage):
    """测试着法数据存储"""
    print("\n♟️ 测试着法数据存储...")
    try:
        # 模拟棋盘状态
        test_board = [[0] * 19 for _ in range(19)]
        test_board[3][3] = 1  # 黑子在D4
        test_board[15][15] = 2  # 白子在P16
        
        # 添加第一步
        storage.add_move_data(
            move_number=1,
            move="D4",
            color="black",
            winrate_data={
                "black_winrate": 52.3,
                "white_winrate": 47.7,
                "score_lead": 1.2
            },
            board=test_board,
            territory_data={
                "black_territory": [[3, 3], [3, 4]],
                "white_territory": [[15, 15], [15, 14]],
                "neutral_points": [[9, 9], [10, 10]]
            },
            recommended_moves=[
                {"position": [15, 3], "winrate": 51.8, "visits": 1000, "score_lead": 0.8},
                {"position": [3, 15], "winrate": 51.5, "visits": 950, "score_lead": 0.6}
            ]
        )
        
        # 添加第二步
        test_board[15][3] = 2  # 白子在P4
        storage.add_move_data(
            move_number=2,
            move="P4",
            color="white",
            winrate_data={
                "black_winrate": 48.1,
                "white_winrate": 51.9,
                "score_lead": -0.8
            },
            board=test_board
        )
        
        print("✅ 着法数据存储测试成功")
        return True
    except Exception as e:
        print(f"❌ 着法数据存储测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_retrieval(storage):
    """测试数据检索"""
    print("\n📖 测试数据检索...")
    try:
        # 获取完整游戏数据
        game_data = storage.get_game_data()
        if game_data:
            print(f"✅ 获取完整游戏数据成功")
            print(f"📊 总步数: {game_data.get('total_moves')}")
            print(f"📈 演化数据条目: {len(game_data.get('evolution_data', []))}")
        
        # 获取演化数据
        evolution_data = storage.get_evolution_data()
        if evolution_data:
            print(f"✅ 获取演化数据成功: {len(evolution_data)} 条记录")
            
            # 显示前几步的详细信息
            for i, move_data in enumerate(evolution_data[:3]):
                print(f"  步骤 {i}: {move_data.get('move')} ({move_data.get('color')})")
                winrate = move_data.get('winrate_data', {})
                print(f"    胜率: 黑{winrate.get('black_winrate', 0):.1f}% 白{winrate.get('white_winrate', 0):.1f}%")
        
        # 获取游戏统计
        stats = storage.get_game_statistics()
        if stats:
            print(f"✅ 获取游戏统计成功")
            print(f"📊 统计信息: {stats}")
        
        return True
    except Exception as e:
        print(f"❌ 数据检索测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_game_status_update(storage):
    """测试游戏状态更新"""
    print("\n🔄 测试游戏状态更新...")
    try:
        # 更新游戏状态为已完成
        storage.update_game_status(
            status="finished",
            final_result={
                "winner": "black",
                "score": "B+2.5",
                "reason": "territory"
            }
        )
        
        # 验证更新
        game_data = storage.get_game_data()
        if game_data and game_data.get('game_status') == 'finished':
            print("✅ 游戏状态更新测试成功")
            print(f"🏆 最终结果: {game_data.get('final_result')}")
            return True
        else:
            print("❌ 游戏状态更新验证失败")
            return False
    except Exception as e:
        print(f"❌ 游戏状态更新测试失败: {e}")
        return False

def test_game_list():
    """测试游戏列表功能"""
    print("\n📋 测试游戏列表功能...")
    try:
        games = GameEvolutionMongoDB.list_games(limit=5)
        if games:
            print(f"✅ 获取游戏列表成功: {len(games)} 个游戏")
            for game in games:
                print(f"  🎮 {game.get('game_id')} - {game.get('game_status')} - {game.get('total_moves')}步")
        else:
            print("⚠️ 游戏列表为空")
        return True
    except Exception as e:
        print(f"❌ 游戏列表测试失败: {e}")
        return False

def cleanup_test_data(storage, test_game_id):
    """清理测试数据"""
    print("\n🧹 清理测试数据...")
    try:
        if storage.delete_game():
            print(f"✅ 测试数据清理成功: {test_game_id}")
        else:
            print(f"⚠️ 测试数据清理失败: {test_game_id}")
    except Exception as e:
        print(f"❌ 清理测试数据异常: {e}")

def main():
    """主测试函数"""
    print("🚀 开始MongoDB存储功能测试")
    print("=" * 50)
    
    # 测试计数器
    total_tests = 0
    passed_tests = 0
    
    # 1. 测试MongoDB连接
    total_tests += 1
    if test_mongodb_connection():
        passed_tests += 1
    else:
        print("❌ MongoDB连接失败，无法继续测试")
        return
    
    # 2. 测试游戏创建
    total_tests += 1
    storage, test_game_id = test_game_creation()
    if storage and test_game_id:
        passed_tests += 1
    else:
        print("❌ 游戏创建失败，无法继续测试")
        return
    
    # 3. 测试着法数据存储
    total_tests += 1
    if test_move_data_storage(storage):
        passed_tests += 1
    
    # 4. 测试数据检索
    total_tests += 1
    if test_data_retrieval(storage):
        passed_tests += 1
    
    # 5. 测试游戏状态更新
    total_tests += 1
    if test_game_status_update(storage):
        passed_tests += 1
    
    # 6. 测试游戏列表
    total_tests += 1
    if test_game_list():
        passed_tests += 1
    
    # 清理测试数据
    cleanup_test_data(storage, test_game_id)
    
    # 测试结果汇总
    print("\n" + "=" * 50)
    print(f"🏁 测试完成: {passed_tests}/{total_tests} 通过")
    
    if passed_tests == total_tests:
        print("🎉 所有测试通过！MongoDB存储功能正常")
        return True
    else:
        print(f"⚠️ {total_tests - passed_tests} 个测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)