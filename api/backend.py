import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import json
import asyncio
from typing import Dict, List, Optional
import uuid
from core.human_vs_katago import WeiQiGame
from core.analysis_game import AnalysisGame
import threading
import time
from ai.ai_handler import ai_handler

# 自动设置NO_PROXY环境变量，避免代理干扰本地服务
os.environ['NO_PROXY'] = 'localhost,127.0.0.1,::1,0.0.0.0'
os.environ['no_proxy'] = 'localhost,127.0.0.1,::1,0.0.0.0'

app = FastAPI(title="围棋对弈系统", description="基于KataGo的围棋人机对弈系统")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 游戏会话管理
game_sessions: Dict[str, WeiQiGame] = {}
active_connections: Dict[str, WebSocket] = {}

class GameManager:
    def __init__(self):
        self.games = {}
        self.connections = {}
        self.session_active = {}  # 跟踪游戏会话是否已开始
    
    async def connect(self, websocket: WebSocket, session_id: str):
        print(f"WebSocket连接请求: session_id={session_id}")
        await websocket.accept()
        print(f"WebSocket连接已接受: session_id={session_id}")
        self.connections[session_id] = websocket
        
        # 创建新游戏会话
        if session_id not in self.games:
            try:
                print(f"创建新游戏实例: session_id={session_id}")
                game = WeiQiGame()
                self.games[session_id] = game
                await self.send_game_state(session_id)
                print(f"游戏状态已发送: session_id={session_id}")
            except Exception as e:
                print(f"游戏初始化失败: session_id={session_id}, error={e}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"游戏初始化失败: {str(e)}"
                }))
    
    async def handle_model_change(self, session_id: str, message: dict):
        """处理AI模型切换请求"""
        websocket = self.connections.get(session_id)
        if not websocket:
            return
            
        try:
            new_model = message.get("model", "")
            if not new_model:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "无效的模型参数"
                }))
                return
            
            # 更新AI处理器的模型
            ai_handler.ai_model = new_model
            print(f"AI模型已切换为: {new_model}")
            
            # 发送确认消息
            await websocket.send_text(json.dumps({
                "type": "model_changed",
                "model": new_model,
                "message": f"AI模型已切换为 {new_model}"
            }))
            
        except Exception as e:
            print(f"模型切换失败: {e}")
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"模型切换失败: {str(e)}"
                }))
    
    def disconnect(self, session_id: str):
        print(f"WebSocket连接断开: session_id={session_id}")
        if session_id in self.connections:
            del self.connections[session_id]
            print(f"已清理连接: session_id={session_id}")
        if session_id in self.games:
            game = self.games[session_id]
            game.cleanup()
            del self.games[session_id]
            print(f"已清理游戏实例: session_id={session_id}")
        if session_id in self.session_active:
            del self.session_active[session_id]
            print(f"已清理会话状态: session_id={session_id}")
    
    async def start_game_session(self, session_id: str):
        """开始游戏会话"""
        self.session_active[session_id] = True
        websocket = self.connections.get(session_id)
        
        # 初始化胜率数据
        if session_id in self.games:
            game = self.games[session_id]
            # 在线程池中执行胜率初始化，避免阻塞
            loop = asyncio.get_event_loop()
            try:
                await loop.run_in_executor(None, game._add_initial_winrate)
            except Exception as e:
                print(f"初始化胜率失败: {e}")
        
        if websocket:
            await websocket.send_text(json.dumps({
                "type": "session_started",
                "message": "游戏会话已开始"
            }))
            # 发送当前游戏状态，包括胜率数据
            await self.send_game_state(session_id)
    
    async def stop_game_session(self, session_id: str):
        """停止游戏会话"""
        self.session_active[session_id] = False
        websocket = self.connections.get(session_id)
        if websocket:
            await websocket.send_text(json.dumps({
                "type": "session_stopped",
                "message": "游戏会话已停止"
            }))
    
    def is_session_active(self, session_id: str) -> bool:
        """检查游戏会话是否已开始"""
        return self.session_active.get(session_id, False)
    
    async def send_game_state(self, session_id: str):
        if session_id not in self.games or session_id not in self.connections:
            return
        
        game = self.games[session_id]
        websocket = self.connections[session_id]
        
        game_state = {
            "type": "game_state",
            "data": {
                "board": game.board,  # 使用真实的棋盘状态
                "moves": game.moves,
                "current_player": game.current_player,
                "game_over": game.game_over,
                "move_count": getattr(game, 'move_count', len(game.moves)),  # 使用实际的move_count
                "captured_black": game.captured_black,
                "captured_white": game.captured_white,
                "winrate_history": game.winrate_history  # 添加胜率历史数据
            }
        }
        
        try:
            await websocket.send_text(json.dumps(game_state))
        except:
            pass
    
    async def make_move(self, session_id: str, move: str, game_mode: str = 'human_vs_ai'):
        if session_id not in self.games:
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        # 根据游戏模式处理不同逻辑
        if game_mode == 'analysis':
            print(f"推演模式落子: session_id={session_id}, move={move}")
            # 推演模式：允许自由落子，不检查回合
            if move == "quit":
                game.game_over = True
                await self.send_game_state(session_id)
                return
            
            # 执行着法（直接传递原始move字符串）
            move_result = game.make_move(move)
            if move_result is False:
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "无效的着法，该位置不能落子"
                    }))
                return
            
            await self.send_game_state(session_id)
            
            # 检查游戏是否结束（双方连续过手）
            if len(game.moves) >= 2 and game.moves[-1][1] == "pass" and game.moves[-2][1] == "pass":
                game.game_over = True
                await self.send_game_state(session_id)
                return
            
            # 推演模式下发送AI分析数据（推荐选点和胜率）
            try:
                analysis_data = await ai_handler.get_ai_analysis(game)
                if analysis_data and websocket:
                    await websocket.send_text(json.dumps({
                        "type": "ai_analysis",
                        "data": analysis_data
                    }))
            except Exception as e:
                print(f"推演模式AI分析失败: {e}")
            
            return
            
        else:
            # Human vs AI模式：检查玩家回合
            if game.current_player != game.player_color:
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "现在不是你的回合"
                    }))
                return
            
            # 验证着法
            parsed_move = game.parse_move(move)
            if parsed_move is None:
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "无效的着法"
                    }))
                return
            
            if parsed_move == "quit":
                game.game_over = True
                await self.send_game_state(session_id)
                return
            
            # 执行人类着法
            move_result = game.make_move(parsed_move)
            if move_result is False:
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "无效的着法，该位置不能落子"
                    }))
                return
            
            await self.send_game_state(session_id)
            
            # 检查游戏是否结束
            if len(game.moves) >= 2 and game.moves[-1][1] == "pass" and game.moves[-2][1] == "pass":
                game.game_over = True
                await self.send_game_state(session_id)
                return
            
            if game.game_over:
                return
            
            # Human vs AI模式下触发AI回合
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "ai_thinking",
                    "message": "KataGo 思考中..."
                }))
            
            # 使用asyncio在后台执行AI着法
            asyncio.create_task(self._get_ai_move_async(session_id))
    
    async def _get_ai_move_async(self, session_id: str):
        """异步获取AI着法"""
        print(f"开始AI异步调用，session_id: {session_id}")
        if session_id not in self.games:
            print(f"session_id {session_id} 不存在于games中")
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        # 检查是否为推演模式，如果是则不执行AI落子
        if hasattr(game, 'is_analysis_mode') and game.is_analysis_mode():
            print(f"推演模式下不执行AI自动落子，session_id: {session_id}")
            return
        
        try:
            # 检查游戏状态
            if game.game_over:
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "游戏已结束"
                    }))
                return
            
            # 使用AI处理器获取着法
            ai_result = await ai_handler.get_ai_move(game, game.ai_time_limit)
            
            if ai_result and ai_result.get('move'):
                ai_move = ai_result['move']
                
                # 执行AI着法
                success = game.make_move(ai_move)
                if not success:
                    if websocket:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "AI着法无效，自动pass"
                        }))
                    game.make_move("pass")
                    ai_move = "pass"
                
                # 发送AI移动结果
                await self._send_ai_result(session_id, {
                    "type": "ai_move",
                    "move": ai_move,
                    "confidence": ai_result.get('confidence', 0.5)
                })
                
                # 发送更新后的游戏状态
                await self.send_game_state(session_id)
                
                # 获取AI分析数据
                try:
                    analysis_data = await ai_handler.get_ai_analysis(game)
                    if analysis_data:
                        # 发送AI分析数据
                        if websocket:
                            await websocket.send_text(json.dumps({
                                "type": "ai_analysis",
                                "data": analysis_data
                            }))
                except Exception as e:
                    print(f"获取AI分析失败: {e}")
            else:
                # AI无法生成着法，自动pass
                game.make_move("pass")
                await self._send_ai_result(session_id, {
                    "type": "ai_move",
                    "move": "pass"
                })
                await self.send_game_state(session_id)
            
        except Exception as e:
            print(f"AI着法失败: {e}")
            await self._send_error(session_id, f"AI着法失败: {str(e)}")
    
    async def _send_ai_result(self, session_id: str, ai_result: dict):
        websocket = self.connections.get(session_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps(ai_result))
                await self.send_game_state(session_id)
                
                # 检查游戏是否结束
                game = self.games.get(session_id)
                if game and len(game.moves) >= 2 and game.moves[-1][1] == "pass" and game.moves[-2][1] == "pass":
                    game.game_over = True
                    await self.send_game_state(session_id)
            except:
                pass
    
    async def _send_error(self, session_id: str, message: str):
        websocket = self.connections.get(session_id)
        if websocket:
            try:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": message
                }))
            except:
                pass
    
    async def undo_move(self, session_id: str):
        if session_id not in self.games or session_id not in self.connections:
            return
        
        game = self.games[session_id]
        websocket = self.connections[session_id]
        
        # 检查是否可以悔棋
        if len(game.moves) == 0:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "没有可以悔棋的着法"
            }))
            return
        
        if game.game_over:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "游戏已结束，无法悔棋"
            }))
            return
        
        try:
            # 悔棋通常需要悔两步（人类和AI的着法）
            undo_count = min(2, len(game.moves))
            for _ in range(undo_count):
                if len(game.moves) > 0:
                    game.undo_last_move()
            
            await self.send_game_state(session_id)
        except Exception as e:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"悔棋失败: {str(e)}"
            }))
    
    async def goto_move(self, session_id: str, move_index: int):
        if session_id not in self.games:
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        try:
            # 回溯到指定着法
            success = game.goto_move(move_index)
            if success:
                await self.send_game_state(session_id)
            else:
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "回溯失败"
                    }))
        except Exception as e:
            if websocket:
                await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"回溯操作失败: {str(e)}"
                    }))

    async def change_player_color(self, session_id: str, color: str):
        """更改玩家执子颜色"""
        if session_id not in self.games:
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        try:
            # 使用游戏对象的方法设置玩家颜色
            if game.change_player_color(color):
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "setting_changed",
                        "setting": "player_color",
                        "value": color,
                        "message": f"玩家执子已设置为{'黑棋' if color == 'B' else '白棋'}"
                    }))
                
                # 如果玩家选择白棋且棋盘为空且游戏会话已开始，AI先落子
                if color == "W" and len(game.moves) == 0 and self.is_session_active(session_id):
                    print(f"玩家选择白棋，棋盘为空，游戏会话已开始，触发AI落子")
                    if websocket:
                        await websocket.send_text(json.dumps({
                            "type": "ai_thinking",
                            "message": "KataGo 思考中..."
                        }))
                    
                    # 让AI先落子
                    asyncio.create_task(self._get_ai_move_async(session_id))
                else:
                    print(f"不触发AI落子：玩家颜色={color}, 棋盘状态=已有{len(game.moves)}步棋, 会话状态={self.is_session_active(session_id)}")
                
                await self.send_game_state(session_id)
            else:
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "无效的玩家颜色设置"
                    }))
        except Exception as e:
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"设置玩家颜色失败: {str(e)}"
                }))

    async def change_ai_strength(self, session_id: str, strength: int):
        """更改AI算力"""
        if session_id not in self.games:
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        try:
            # 使用AI处理器设置强度
            success = await ai_handler.set_ai_strength(game, strength)
            
            if success:
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "setting_changed",
                        "setting": "ai_strength",
                        "value": strength,
                        "message": f"AI算力已设置为{strength}秒"
                    }))
            else:
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "无效的AI算力设置"
                    }))
        except Exception as e:
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"设置AI算力失败: {str(e)}"
                }))

    async def change_komi(self, session_id: str, komi: float):
        """更改贴目"""
        if session_id not in self.games:
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        try:
            # 使用游戏对象的方法设置贴目
            if game.change_komi(komi):
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "setting_changed",
                        "setting": "komi",
                        "value": komi,
                        "message": f"贴目已设置为{komi}目"
                    }))
            else:
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "无效的贴目设置"
                    }))
        except Exception as e:
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"设置贴目失败: {str(e)}"
                }))

    async def change_rules(self, session_id: str, rules: str):
        """更改规则"""
        if session_id not in self.games:
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        try:
            # 使用游戏对象的方法设置规则
            if game.change_rules(rules):
                rules_name = {
                    'chinese': '中国规则',
                    'japanese': '日本规则', 
                    'korean': '韩国规则'
                }.get(rules, rules)
                
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "setting_changed",
                        "setting": "rules",
                        "value": rules,
                        "message": f"规则已设置为{rules_name}"
                    }))
            else:
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "无效的规则设置"
                    }))
        except Exception as e:
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"设置规则失败: {str(e)}"
                }))

    async def change_suggestion_ai_strength(self, session_id: str, strength: int):
        """更改推荐选点AI算力"""
        if session_id not in self.games:
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        try:
            # 使用游戏对象的方法设置推荐选点AI算力
            if game.change_suggestion_ai_strength(strength):
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "setting_changed",
                        "setting": "suggestion_ai_strength",
                        "value": strength,
                        "message": f"推荐选点AI算力已设置为{strength}秒"
                    }))
            else:
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "无效的推荐选点AI算力设置"
                    }))
        except Exception as e:
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"设置推荐选点AI算力失败: {str(e)}"
                }))

    async def start_realtime_suggestions(self, session_id: str):
        """开始实时推荐选点"""
        if session_id not in self.games:
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        try:
            # 确保KataGo已启动
            if not game.katago_initialized:
                game._start_katago()
            
            # 定义回调函数，用于发送实时推荐数据
            async def suggestion_callback(suggestions):
                if websocket and session_id in self.connections:
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "realtime_suggestions",
                            "data": suggestions
                        }))
                    except Exception as e:
                        print(f"发送实时推荐失败: {e}")
            
            # 使用推荐选点专用的算力设置
            max_visits = max(1, int(game.suggestion_ai_time_limit * 100))  # 确保为正整数
            
            # 在线程池中启动实时分析
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                game.start_realtime_analysis, 
                lambda suggestions: asyncio.create_task(suggestion_callback(suggestions)),
                max_visits
            )
            
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "realtime_suggestions_started",
                    "message": "实时推荐选点已启动"
                }))
                
        except Exception as e:
            print(f"启动实时推荐失败: {e}")
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"启动实时推荐失败: {str(e)}"
                }))
    
    async def stop_realtime_suggestions(self, session_id: str):
        """停止实时推荐选点"""
        if session_id not in self.games:
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        try:
            game.stop_realtime_analysis()
            
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "realtime_suggestions_stopped",
                    "message": "实时推荐选点已停止"
                }))
                
        except Exception as e:
            print(f"停止实时推荐失败: {e}")
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"停止实时推荐失败: {str(e)}"
                }))

    async def handle_ai_commentary(self, session_id: str, message: dict):
        """处理AI讲棋请求"""
        websocket = self.connections.get(session_id)
        if not websocket:
            return
            
        try:
            if session_id not in self.games:
                await websocket.send_text(json.dumps({
                    "type": "ai_commentary_response",
                    "content": "游戏尚未开始，无法进行讲棋分析。"
                }))
                return
                
            game = self.games[session_id]
            
            # 根据消息类型处理
            if message.get("message_type") == "move_commentary":
                # 着法解说
                move_info = message.get("move", {})
                commentary = await ai_handler.generate_move_commentary(game, move_info)
            elif message.get("message_type") == "user_question":
                # 用户提问
                user_question = message.get("message", "")
                commentary = await ai_handler.generate_user_response(game, user_question)
            else:
                commentary = "抱歉，我无法理解您的请求。"
            
            await websocket.send_text(json.dumps({
                "type": "ai_commentary_response",
                "content": commentary
            }))
            
        except Exception as e:
            print(f"AI讲棋处理失败: {e}")
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "ai_commentary_response",
                    "content": "抱歉，AI讲棋服务暂时不可用，请稍后再试。"
                }))
    
    async def calculate_territory_score(self, session_id: str):
        """计算终局点目"""
        if session_id not in self.games:
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        if not websocket:
            return
        
        try:
            # 检查对局是否结束
            is_finished = await ai_handler.is_game_finished(game)
            
            if not is_finished:
                await websocket.send_text(json.dumps({
                    "type": "territory_score_response",
                    "error": "对局尚未结束，无法进行点目计算。请双方都pass后再试。"
                }))
                return
            
            # 计算点目
            territory_result = await ai_handler.calculate_territory_score(game)
            
            if territory_result:
                await websocket.send_text(json.dumps({
                    "type": "territory_score_response",
                    "result": territory_result
                }))
            else:
                await websocket.send_text(json.dumps({
                    "type": "territory_score_response",
                    "error": "点目计算失败，请稍后再试。"
                }))
                
        except Exception as e:
            print(f"点目计算失败: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "点目计算功能暂时不可用，请稍后再试。"
            }))
    
    async def get_territory_preview(self, session_id: str):
        """获取领地预览（不要求对局结束）"""
        print(f"收到领地预览请求: session_id={session_id}")
        
        if session_id not in self.games:
            print(f"session_id {session_id} 不存在于games中")
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        if not websocket:
            print(f"session_id {session_id} 没有对应的websocket连接")
            return
        
        try:
            print(f"开始获取领地所有权数据...")
            # 获取当前局面的领地所有权数据
            territory_result = await ai_handler.get_territory_ownership(game)
            print(f"领地所有权数据获取结果: {territory_result.get('success', False)}")
            
            if territory_result.get("success"):
                print(f"发送成功的领地预览响应")
                await websocket.send_text(json.dumps({
                    "type": "territory_preview_response",
                    "result": territory_result
                }))
            else:
                print(f"发送失败的领地预览响应: {territory_result.get('error')}")
                await websocket.send_text(json.dumps({
                    "type": "territory_preview_response",
                    "error": territory_result.get("error", "领地分析失败，请稍后再试。")
                }))
                
        except Exception as e:
            print(f"领地预览失败: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "领地预览功能暂时不可用，请稍后再试。"
            }))
    
    async def import_sgf(self, session_id: str, sgf_content: str):
        """导入SGF文件"""
        print(f"收到SGF导入请求: session_id={session_id}")
        
        if session_id not in self.games:
            print(f"session_id {session_id} 不存在于games中")
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        if not websocket:
            print(f"session_id {session_id} 没有对应的websocket连接")
            return
        
        # 检查是否为推演模式
        if not isinstance(game, AnalysisGame):
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "SGF导入功能仅在推演模式下可用"
            }))
            return
        
        try:
            # 创建动态落子的回调函数
            async def move_callback():
                # 发送当前棋盘状态
                await self.send_game_state(session_id)
                # 添加延迟以展示动态落子效果
                await asyncio.sleep(0.5)
            
            # 解析SGF内容并加载到游戏中，传入回调函数
            success = await game.load_from_sgf_async(sgf_content, move_callback)
            
            if success:
                print(f"SGF文件导入成功")
                await websocket.send_text(json.dumps({
                    "type": "sgf_import_success",
                    "message": "SGF文件导入成功"
                }))
            else:
                print(f"SGF文件解析失败")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "SGF文件格式错误或解析失败"
                }))
                
        except Exception as e:
            print(f"SGF导入失败: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"SGF导入失败: {str(e)}"
            }))
    
    async def get_ai_suggestions(self, session_id: str):
        """获取AI推荐选点"""
        print(f"收到AI推荐选点请求: session_id={session_id}")
        
        if session_id not in self.games:
            print(f"session_id {session_id} 不存在于games中")
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        if not websocket:
            print(f"session_id {session_id} 没有对应的websocket连接")
            return
        
        try:
            # 获取AI分析数据（包含推荐选点）
            analysis_data = await ai_handler.get_ai_analysis(game)
            if analysis_data and websocket:
                await websocket.send_text(json.dumps({
                    "type": "ai_analysis",
                    "data": analysis_data
                }))
                print(f"AI推荐选点发送成功: session_id={session_id}")
            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "无法获取AI推荐选点"
                }))
        except Exception as e:
            print(f"获取AI推荐选点失败: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"获取AI推荐选点失败: {str(e)}"
            }))
    
    async def get_game_evolution_data(self, session_id: str):
        """获取对局局势演化数据"""
        if session_id not in self.games:
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        try:
            # 获取局势演化存储系统的统计信息
            evolution_stats = game.evolution_storage.get_statistics()
            
            # 获取最新的局势数据
            latest_data = game.evolution_storage.get_latest_data()
            
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "game_evolution_data",
                    "data": {
                        "statistics": evolution_stats,
                        "latest_move_data": latest_data,
                        "total_moves": len(game.evolution_storage.evolution_data) - 1  # 减去初始状态
                    }
                }))
                
        except Exception as e:
            print(f"获取局势演化数据失败: {e}")
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"获取局势演化数据失败: {str(e)}"
                }))
    
    async def get_move_evolution_data(self, session_id: str, move_number: int):
        """获取指定手数的局势演化数据"""
        if session_id not in self.games:
            return
        
        game = self.games[session_id]
        websocket = self.connections.get(session_id)
        
        try:
            # 获取指定手数的数据
            move_data = game.evolution_storage.get_move_data(move_number)
            
            if move_data and websocket:
                await websocket.send_text(json.dumps({
                    "type": "move_evolution_data",
                    "data": move_data
                }))
            else:
                if websocket:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"未找到第{move_number}手的数据"
                    }))
                    
        except Exception as e:
            print(f"获取指定手数局势数据失败: {e}")
            if websocket:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"获取指定手数局势数据失败: {str(e)}"
                }))


manager = GameManager()

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            print(f"收到WebSocket消息: session_id={session_id}, message_type={message.get('type')}, data={data}")
            
            if message["type"] == "make_move":
                game_mode = message.get("game_mode", "human_vs_ai")
                print(f"make_move消息: session_id={session_id}, move={message['move']}, game_mode={game_mode}")
                await manager.make_move(session_id, message["move"], game_mode)
            elif message["type"] == "new_game":
                # 重新开始游戏
                game_mode = message.get("game_mode", "human_vs_ai")
                print(f"new_game消息: session_id={session_id}, game_mode={game_mode}")
                old_game = None
                if session_id in manager.games:
                    old_game = manager.games[session_id]
                    old_game.cleanup()
                try:
                    # 根据游戏模式创建不同的游戏实例
                    if game_mode == 'analysis':
                        print(f"创建推演模式游戏实例: session_id={session_id}")
                        game = AnalysisGame()
                    else:
                        print(f"创建Human vs AI模式游戏实例: session_id={session_id}")
                        game = WeiQiGame()
                    
                    # 保持之前的游戏设置
                    if old_game:
                        game.player_color = old_game.player_color
                        game.ai_time_limit = old_game.ai_time_limit
                        game.komi = old_game.komi
                        game.rules = old_game.rules
                    
                    manager.games[session_id] = game
                    
                    # 如果游戏会话已开始，初始化胜率数据
                    if manager.is_session_active(session_id):
                        loop = asyncio.get_event_loop()
                        try:
                            await loop.run_in_executor(None, game._add_initial_winrate)
                        except Exception as e:
                            print(f"新游戏初始化胜率失败: {e}")
                    
                    await manager.send_game_state(session_id)
                    
                    # 只在Human vs AI模式下，如果玩家选择白棋且游戏会话已开始，AI先落子
                    if game_mode == 'human_vs_ai' and game.player_color == "W" and manager.is_session_active(session_id):
                        print(f"新游戏：Human vs AI模式，玩家选择白棋，当前轮到{game.current_player}，游戏会话已开始，触发AI落子")
                        await websocket.send_text(json.dumps({
                            "type": "ai_thinking",
                            "message": "KataGo 思考中..."
                        }))
                        # 直接让AI（黑棋）先落子，不需要pass
                        asyncio.create_task(manager._get_ai_move_async(session_id))
                    else:
                        print(f"新游戏：模式={game_mode}，玩家选择{game.player_color}，会话状态={manager.is_session_active(session_id)}，不触发AI落子")
                        
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"游戏重新开始失败: {str(e)}"
                    }))
            elif message["type"] == "undo_move":
                await manager.undo_move(session_id)
            elif message["type"] == "goto_move":
                await manager.goto_move(session_id, message["move_index"])
            elif message["type"] == "change_player_color":
                print(f"收到change_player_color消息: session_id={session_id}, color={message['color']}")
                await manager.change_player_color(session_id, message["color"])
            elif message["type"] == "change_ai_strength":
                try:
                    strength = float(message["strength"])
                    await manager.change_ai_strength(session_id, strength)
                except (ValueError, TypeError):
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "无效的AI算力值"
                    }))
            elif message["type"] == "change_komi":
                await manager.change_komi(session_id, message["komi"])
            elif message["type"] == "change_rules":
                await manager.change_rules(session_id, message["rules"])
            elif message["type"] == "change_suggestion_ai_strength":
                try:
                    strength = int(message["strength"])
                    await manager.change_suggestion_ai_strength(session_id, strength)
                except (ValueError, TypeError):
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "无效的AI算力值"
                    }))
            elif message["type"] == "start_game_session":
                await manager.start_game_session(session_id)
            elif message["type"] == "stop_game_session":
                await manager.stop_game_session(session_id)
            elif message["type"] == "ai_commentary":
                await manager.handle_ai_commentary(session_id, message)
            elif message["type"] == "change_model":
                await manager.handle_model_change(session_id, message)
            elif message["type"] == "start_realtime_suggestions":
                await manager.start_realtime_suggestions(session_id)
            elif message["type"] == "stop_realtime_suggestions":
                await manager.stop_realtime_suggestions(session_id)
            elif message["type"] == "calculate_territory_score":
                await manager.calculate_territory_score(session_id)
            elif message["type"] == "get_territory_preview":
                await manager.get_territory_preview(session_id)
            elif message["type"] == "import_sgf":
                await manager.import_sgf(session_id, message["sgf_content"])
            elif message["type"] == "get_ai_suggestions":
                await manager.get_ai_suggestions(session_id)
            elif message["type"] == "get_game_evolution_data":
                await manager.get_game_evolution_data(session_id)
            elif message["type"] == "get_move_evolution_data":
                move_number = message.get("move_number", 0)
                await manager.get_move_evolution_data(session_id, move_number)
    except WebSocketDisconnect:
        manager.disconnect(session_id)

@app.get("/")
async def read_root():
    return {"message": "围棋对弈系统后端API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/models")
async def get_available_models():
    """获取可用的AI模型列表"""
    try:
        models = await ai_handler.get_available_models()
        return {"models": models}
    except Exception as e:
        return {"error": f"获取模型列表失败: {str(e)}", "models": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)