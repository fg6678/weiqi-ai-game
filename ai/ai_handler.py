import openai
import httpx
import os
import asyncio
from typing import Dict, Optional, List
from storage.game_evolution_mongodb import GameEvolutionMongoDB

class AIHandler:
    """AI处理器 - 负责处理所有AI相关的请求"""
    
    def __init__(self):
        self.ai_model = "qwen3:4b-instruct"#qwen3:30b-a3b-instruct-2507-q4_K_M
        self.base_url = "http://localhost:11434/v1"
        self.api_key = "ollama"  # ollama不需要真实的API key
    
    async def get_ai_move(self, game, strength: int = 1600) -> Optional[Dict]:
        """获取AI着法"""
        try:
            if not game:
                return None
            
            # 设置AI强度（通过ai_time_limit属性）
            if hasattr(game, 'ai_time_limit'):
                game.ai_time_limit = max(1, min(100, strength / 100))  # 转换为时间限制
            
            # 获取AI着法
            ai_move = await asyncio.to_thread(game.get_katago_move)
            
            if ai_move and ai_move != "pass":
                return {
                    "move": ai_move,
                    "strength": strength,
                    "confidence": 0.8  # 默认置信度
                }
            elif ai_move == "pass":
                return {
                    "move": "pass",
                    "strength": strength,
                    "confidence": 0.5
                }
            
            return None
            
        except Exception as e:
            print(f"获取AI着法失败: {e}")
            return None
    
    async def get_move_suggestions(self, game, num_suggestions: int = 5) -> List[Dict]:
        """获取着法建议"""
        try:
            if not game or not hasattr(game, 'katago'):
                return []
            
            # 获取多个候选着法
            suggestions = await asyncio.to_thread(game.katago.get_suggestions, num_suggestions)
            
            if suggestions:
                return [
                    {
                        "move": suggestion.get("move", ""),
                        "winrate": suggestion.get("winrate", 0.5),
                        "visits": suggestion.get("visits", 0),
                        "score": suggestion.get("score", 0.0)
                    }
                    for suggestion in suggestions
                ]
            
            return []
            
        except Exception as e:
            print(f"获取着法建议失败: {e}")
            return []
    
    async def generate_move_commentary(self, game, move_info: Dict) -> str:
        """生成着法解说"""
        try:
            board_desc = self._get_board_description(game)
            move = move_info.get('move', '')
            player = move_info.get('player', '')
            
            prompt = f"""
当前局面：{board_desc}
刚下的棋：{player}在{move}位置落子

请简要分析这手棋的意图和效果，包括：
1. 这手棋的战略意图
2. 对局面的影响
3. 后续可能的发展

请用简洁的语言回答，不超过100字。
"""
            
            return await self._call_ai_model(prompt)
            
        except Exception as e:
            print(f"生成着法解说失败: {e}")
            return "无法生成解说，请稍后再试。"
    
    async def generate_user_response(self, game, question: str) -> str:
        """生成用户问题回答"""
        try:
            board_desc = self._get_board_description(game)
            
            # 获取MongoDB中的最近游戏记录
            recent_game_data = self._get_recent_game_data(game)
            
            prompt = f"""
当前局面：{board_desc}

最近游戏数据：
{recent_game_data}

用户问题：{question}

请根据当前棋局情况和最近的游戏数据回答用户的问题。如果问题与当前局面相关，请结合具体情况和历史数据分析；如果是一般性围棋问题，请给出专业的建议。

请用简洁明了的语言回答，不超过200字。
"""
            
            return await self._call_ai_model(prompt)
            
        except Exception as e:
            print(f"生成用户回答失败: {e}")
            return "抱歉，无法回答您的问题，请稍后再试。"
    
    def _get_board_description(self, game) -> str:
        """获取棋盘状态描述"""
        try:
            move_count = len(game.moves)
            current_player = "黑棋" if game.current_player == "B" else "白棋"
            
            # 简单的局面描述
            if move_count == 0:
                return "空棋盘，游戏刚开始"
            elif move_count < 10:
                return f"序盘阶段，已下{move_count}手，轮到{current_player}"
            elif move_count < 50:
                return f"布局阶段，已下{move_count}手，轮到{current_player}"
            elif move_count < 100:
                return f"中盘阶段，已下{move_count}手，轮到{current_player}"
            else:
                return f"官子阶段，已下{move_count}手，轮到{current_player}"
                
        except Exception as e:
            print(f"获取棋盘描述失败: {e}")
            return "当前局面"
    
    def _get_recent_game_data(self, game) -> str:
        """获取MongoDB中的最近游戏记录"""
        try:
            # 获取当前游戏的演化数据
            if hasattr(game, 'evolution_storage') and game.evolution_storage:
                evolution_data = game.evolution_storage.get_evolution_data()
                if evolution_data:
                    # 获取最近5步的数据
                    recent_moves = evolution_data[-5:] if len(evolution_data) > 5 else evolution_data
                    
                    game_data_summary = []
                    for i, move_data in enumerate(recent_moves):
                        move_num = move_data.get('move_number', i)
                        move = move_data.get('move', 'N/A')
                        color = move_data.get('color', 'N/A')
                        winrate_data = move_data.get('winrate_data', {})
                        black_wr = winrate_data.get('black_winrate', 0) * 100
                        white_wr = winrate_data.get('white_winrate', 0) * 100
                        recommended_moves = move_data.get('recommended_moves', [])
                        
                        color_name = "黑棋" if color == "B" else "白棋" if color == "W" else "开始"
                        
                        summary = f"第{move_num}步: {move} ({color_name}) - 黑棋胜率{black_wr:.1f}% 白棋胜率{white_wr:.1f}%"
                        if recommended_moves:
                            top_moves = [m.get('move', '') for m in recommended_moves[:3]]
                            summary += f" - AI推荐: {', '.join(top_moves)}"
                        
                        game_data_summary.append(summary)
                    
                    return "\n".join(game_data_summary)
            
            # 如果没有当前游戏数据，尝试获取最近的游戏列表
            recent_games = GameEvolutionMongoDB.list_games(limit=3)
            if recent_games:
                games_summary = []
                for game_info in recent_games:
                    game_id = game_info.get('game_id', 'N/A')
                    total_moves = game_info.get('total_moves', 0)
                    status = game_info.get('game_status', 'unknown')
                    games_summary.append(f"游戏{game_id}: {total_moves}步, 状态:{status}")
                
                return "最近游戏记录:\n" + "\n".join(games_summary)
            
            return "暂无最近游戏数据"
            
        except Exception as e:
            print(f"获取最近游戏数据失败: {e}")
            return "无法获取最近游戏数据"
    
    async def _call_ai_model(self, prompt: str) -> str:
        """调用AI模型生成回答"""
        try:
            # 创建一个不使用代理的httpx客户端
            # 设置环境变量来绕过代理
            original_http_proxy = os.environ.get('HTTP_PROXY')
            original_https_proxy = os.environ.get('HTTPS_PROXY')
            original_http_proxy_lower = os.environ.get('http_proxy')
            original_https_proxy_lower = os.environ.get('https_proxy')
            
            # 临时移除代理环境变量
            if 'HTTP_PROXY' in os.environ:
                del os.environ['HTTP_PROXY']
            if 'HTTPS_PROXY' in os.environ:
                del os.environ['HTTPS_PROXY']
            if 'http_proxy' in os.environ:
                del os.environ['http_proxy']
            if 'https_proxy' in os.environ:
                del os.environ['https_proxy']
            
            # 创建不使用代理的httpx客户端
            http_client = httpx.AsyncClient(
                timeout=30.0
            )
            
            # 配置OpenAI客户端连接到本地ollama
            client = openai.AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                http_client=http_client
            )
            
            try:
                response = await client.chat.completions.create(
                    model=self.ai_model,
                    messages=[
                        {"role": "system", "content": "你是一位专业的围棋讲解员和老师，擅长用简洁明了的语言分析棋局和回答围棋相关问题。"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.7
                )
                
                return response.choices[0].message.content.strip()
                
            finally:
                # 恢复原来的代理环境变量
                if original_http_proxy is not None:
                    os.environ['HTTP_PROXY'] = original_http_proxy
                if original_https_proxy is not None:
                    os.environ['HTTPS_PROXY'] = original_https_proxy
                if original_http_proxy_lower is not None:
                    os.environ['http_proxy'] = original_http_proxy_lower
                if original_https_proxy_lower is not None:
                    os.environ['https_proxy'] = original_https_proxy_lower
                
                # 关闭httpx客户端
                await http_client.aclose()
            
        except Exception as e:
            print(f"调用AI模型失败: {e}")
            return "AI服务暂时不可用，请稍后再试。"
    
    async def set_ai_strength(self, game, strength: int) -> bool:
        """设置AI强度"""
        try:
            if not game:
                return False
            
            # 限制强度范围并转换为时间限制
            strength = max(100, min(10000, strength))
            time_limit = max(1, min(100, strength / 100))  # 转换为1-100的时间限制
            
            if hasattr(game, 'ai_time_limit'):
                game.ai_time_limit = time_limit
                return True
            
            return False
            
        except Exception as e:
            print(f"设置AI强度失败: {e}")
            return False
    
    async def analyze_position(self, game) -> Dict:
        """分析当前局面"""
        try:
            if not game or not hasattr(game, 'katago'):
                return {}
            
            # 获取局面分析
            analysis = await asyncio.to_thread(game.katago.analyze_position)
            
            if analysis:
                return {
                    "winrate": analysis.get("winrate", 0.5),
                    "score": analysis.get("score", 0.0),
                    "best_moves": analysis.get("best_moves", []),
                    "territory": analysis.get("territory", {})
                }
            
            return {}
            
        except Exception as e:
            print(f"分析局面失败: {e}")
            return {}
    
    async def get_ai_analysis(self, game) -> List[Dict]:
        """获取AI分析数据"""
        try:
            if not game:
                return []
            
            # 获取分析结果
            analysis_result = await asyncio.to_thread(game._send_analysis_request)
            move_infos = analysis_result.get("moveInfos", [])
            
            ai_analysis_data = []
            for i, mv in enumerate(move_infos[:5]):
                ai_analysis_data.append({
                    "move": mv["move"],
                    "winrate": mv["winrate"],
                    "score_lead": mv.get("scoreLead", 0)
                })
            
            return ai_analysis_data
            
        except Exception as e:
            print(f"获取AI分析失败: {e}")
            return []
    
    async def calculate_territory_score(self, game) -> Dict:
        """计算终局点目"""
        try:
            if not game:
                return {}
            
            # 获取包含ownership信息的分析结果
            analysis_result = await asyncio.to_thread(game._send_analysis_request, 500)  # 使用更多访问次数获得准确结果
            
            if not analysis_result:
                return {}
            
            ownership = analysis_result.get("ownership", [])
            if not ownership:
                return {}
            
            # 计算领地和点目
            territory_info = self._analyze_ownership(ownership, game.board_size, game)
            
            # 获取当前比分
            move_infos = analysis_result.get("moveInfos", [])
            current_score = 0
            if move_infos:
                current_score = move_infos[0].get("scoreLead", 0)
            
            # 计算最终比分（考虑贴目）
            black_territory = territory_info["black_territory"]
            white_territory = territory_info["white_territory"]
            black_prisoners = territory_info["black_prisoners"]
            white_prisoners = territory_info["white_prisoners"]
            
            # 中国规则：子数 + 活棋围成的空点
            black_score = black_territory + black_prisoners
            white_score = white_territory + white_prisoners + game.komi
            
            score_difference = black_score - white_score
            winner = "黑棋" if score_difference > 0 else "白棋"
            
            return {
                "black_territory": black_territory,
                "white_territory": white_territory,
                "black_prisoners": black_prisoners,
                "white_prisoners": white_prisoners,
                "black_score": round(black_score, 1),
                "white_score": round(white_score, 1),
                "score_difference": round(abs(score_difference), 1),
                "winner": winner,
                "komi": game.komi,
                "current_score_lead": round(current_score, 1),
                "territory_map": territory_info["territory_map"]
            }
            
        except Exception as e:
            print(f"计算点目失败: {e}")
            return {}
    
    def _analyze_ownership(self, ownership: List[float], board_size: int, game=None) -> Dict:
        """分析ownership数据，计算领地信息"""
        territory_map = []
        black_territory = 0
        white_territory = 0
        
        # 从游戏对象获取被提子数
        black_prisoners = 0
        white_prisoners = 0
        if game:
            black_prisoners = getattr(game, 'captured_black', 0)
            white_prisoners = getattr(game, 'captured_white', 0)
        
        # ownership是一维数组，需要转换为二维
        for i in range(board_size):
            row = []
            for j in range(board_size):
                idx = i * board_size + j
                if idx < len(ownership):
                    ownership_value = ownership[idx]
                    
                    # ownership值：正数表示黑棋领地，负数表示白棋领地
                    # 绝对值越大表示确定性越高
                    if ownership_value > 0.7:  # 黑棋确定领地
                        row.append("B")
                        black_territory += 1
                    elif ownership_value < -0.7:  # 白棋确定领地
                        row.append("W")
                        white_territory += 1
                    else:  # 争议区域
                        row.append("?")
                else:
                    row.append("?")
            territory_map.append(row)
        
        return {
            "black_territory": black_territory,
            "white_territory": white_territory,
            "black_prisoners": black_prisoners,
            "white_prisoners": white_prisoners,
            "territory_map": territory_map
        }
    
    async def get_available_models(self) -> List[Dict]:
        """获取ollama可用模型列表"""
        try:
            # 临时移除代理环境变量
            original_proxies = {}
            proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
            for var in proxy_vars:
                if var in os.environ:
                    original_proxies[var] = os.environ[var]
                    del os.environ[var]
            
            try:
                # 创建不使用代理的httpx客户端
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get("http://localhost:11434/api/tags")
                    
                    if response.status_code == 200:
                        data = response.json()
                        models = []
                        for model in data.get('models', []):
                            model_name = model.get('name', '')
                            # 过滤出常用的聊天模型
                            if any(keyword in model_name.lower() for keyword in ['qwen', 'llama', 'gemma', 'mistral', 'phi']):
                                models.append({
                                    'label': model_name,  # 显示完整模型名称
                                    'value': model_name
                                })
                        return models
                    else:
                        print(f"获取模型列表失败，状态码: {response.status_code}")
                        return []
            finally:
                # 恢复代理环境变量
                for var, value in original_proxies.items():
                    os.environ[var] = value
                    
        except Exception as e:
            print(f"获取ollama模型列表失败: {e}")
            # 返回默认模型列表作为备选
            return [
                {'label': 'qwen3:4b-instruct', 'value': 'qwen3:4b-instruct'},
                {'label': 'qwen3:30b-instruct', 'value': 'qwen3:30b-instruct'}
            ]
    
    async def is_game_finished(self, game) -> bool:
        """检查游戏是否结束"""
        try:
            if not game or len(game.moves) < 2:
                return False
            
            # 检查是否连续两次pass
            last_two_moves = game.moves[-2:]
            return all(move[1] == "pass" for move in last_two_moves)
            
        except Exception as e:
            print(f"检查游戏状态失败: {e}")
            return False
    
    async def get_territory_ownership(self, game) -> Dict:
        """获取领地所有权数据（用于前端可视化）"""
        try:
            if not game:
                return {}
            
            # 发送分析请求获取ownership数据
            analysis_result = await asyncio.to_thread(game._send_analysis_request)
            
            if analysis_result and 'ownership' in analysis_result:
                ownership_1d = analysis_result['ownership']
                board_size = game.board_size
                
                print(f"KataGo返回的ownership数据长度: {len(ownership_1d)}")
                print(f"期望的数据长度: {board_size * board_size}")
                
                # 将一维数组转换为二维数组
                if len(ownership_1d) == board_size * board_size:
                    ownership_2d = []
                    for row in range(board_size):
                        row_data = []
                        for col in range(board_size):
                            index = row * board_size + col
                            row_data.append(ownership_1d[index])
                        ownership_2d.append(row_data)
                    
                    print(f"成功转换为{len(ownership_2d)}x{len(ownership_2d[0])}的二维数组")
                    
                    return {
                        "ownership": ownership_2d,
                        "board_size": board_size,
                        "success": True
                    }
                else:
                    print(f"ownership数据长度不匹配: 期望{board_size * board_size}, 实际{len(ownership_1d)}")
                    return {
                        "success": False,
                        "error": f"ownership数据长度不匹配: 期望{board_size * board_size}, 实际{len(ownership_1d)}"
                    }
            else:
                return {
                    "success": False,
                    "error": "无法获取领地数据"
                }
                
        except Exception as e:
            print(f"获取领地所有权数据失败: {e}")
            return {
                "success": False,
                "error": f"获取领地数据失败: {str(e)}"
            }

ai_handler = AIHandler()