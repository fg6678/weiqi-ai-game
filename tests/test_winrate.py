#!/usr/bin/env python3
"""
测试胜率计算逻辑
"""

import json
from core.human_vs_katago import WeiQiGame

def test_winrate_calculation():
    """测试不同贴目设置下的胜率计算"""
    
    # 测试贴目为0的情况
    print("=== 测试贴目为0的情况 ===")
    game = WeiQiGame()
    game.komi = 0.0
    
    try:
        game._start_katago()
        result = game._send_analysis_request(max_visits=100)
        move_infos = result.get('moveInfos', [])
        
        if move_infos:
            best_move = move_infos[0]
            winrate = best_move['winrate']
            print(f"KataGo返回的胜率: {winrate:.4f} ({winrate*100:.1f}%)")
            print(f"当前下棋方: {game.current_player}")
            
            # 模拟前端的胜率计算逻辑
            winrate_percent = winrate * 100
            if game.current_player == 'B':
                black_winrate = round(max(0, min(100, winrate_percent)) * 10) / 10
                white_winrate = round((100 - black_winrate) * 10) / 10
            else:
                white_winrate = round(max(0, min(100, winrate_percent)) * 10) / 10
                black_winrate = round((100 - white_winrate) * 10) / 10
                
            print(f"计算后的黑棋胜率: {black_winrate}%")
            print(f"计算后的白棋胜率: {white_winrate}%")
            
        else:
            print("未获取到分析结果")
            
    except Exception as e:
        print(f"错误: {e}")
    finally:
        if game.proc:
            game.proc.terminate()
    
    print("\n=== 测试贴目为6.5的情况 ===")
    game2 = WeiQiGame()
    game2.komi = 6.5
    
    try:
        game2._start_katago()
        result = game2._send_analysis_request(max_visits=100)
        move_infos = result.get('moveInfos', [])
        
        if move_infos:
            best_move = move_infos[0]
            winrate = best_move['winrate']
            print(f"KataGo返回的胜率: {winrate:.4f} ({winrate*100:.1f}%)")
            print(f"当前下棋方: {game2.current_player}")
            
            # 模拟前端的胜率计算逻辑
            winrate_percent = winrate * 100
            if game2.current_player == 'B':
                black_winrate = round(max(0, min(100, winrate_percent)) * 10) / 10
                white_winrate = round((100 - black_winrate) * 10) / 10
            else:
                white_winrate = round(max(0, min(100, winrate_percent)) * 10) / 10
                black_winrate = round((100 - white_winrate) * 10) / 10
                
            print(f"计算后的黑棋胜率: {black_winrate}%")
            print(f"计算后的白棋胜率: {white_winrate}%")
            
        else:
            print("未获取到分析结果")
            
    except Exception as e:
        print(f"错误: {e}")
    finally:
        if game2.proc:
            game2.proc.terminate()

if __name__ == "__main__":
    test_winrate_calculation()