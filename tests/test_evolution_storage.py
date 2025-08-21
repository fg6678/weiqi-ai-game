#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from legacy.game_evolution_storage import GameEvolutionStorage

def test_evolution_storage():
    print("=== 测试局势演化存储系统 ===")
    
    # 创建存储实例
    storage = GameEvolutionStorage("test_game")
    print(f"创建存储实例，游戏ID: {storage.game_id}")
    print(f"存储路径: {storage.storage_path}")
    
    # 创建测试棋盘
    board = [[0 for _ in range(19)] for _ in range(19)]
    board[3][3] = 1  # 黑子
    board[15][15] = 2  # 白子
    
    # 添加测试数据
    winrate_data = {
        "black_winrate": 55.0,
        "white_winrate": 45.0,
        "score_lead": 2.5
    }
    
    recommended_moves = [
        {"move": "D4", "winrate": 0.6, "visits": 100},
        {"move": "Q16", "winrate": 0.55, "visits": 80}
    ]
    
    ownership_data = {}
    
    try:
        storage.add_move_data(
            move_number=1,
            move="D4",
            color="black",
            board=board,
            winrate_data=winrate_data,
            recommended_moves=recommended_moves,
            ownership_data=ownership_data
        )
        print("✓ 成功添加第1步数据")
        
        # 保存到文件
        storage.save_to_file()
        print("✓ 成功保存到文件")
        
        # 检查文件是否存在
        if os.path.exists(storage.storage_path):
            print(f"✓ 文件已创建: {storage.storage_path}")
            
            # 读取文件内容
            with open(storage.storage_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"文件大小: {len(content)} 字符")
                print("文件内容前200字符:")
                print(content[:200])
        else:
            print("✗ 文件未创建")
            
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_evolution_storage()