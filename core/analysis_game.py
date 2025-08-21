import json
from .human_vs_katago import WeiQiGame
from storage.game_evolution_mongodb import GameEvolutionMongoDB
try:
    from sgfmill import sgf
except ImportError:
    sgf = None

class AnalysisGame(WeiQiGame):
    """
    推演模式游戏类
    继承自WeiQiGame，但禁用AI自动落子功能
    专门用于棋局分析和推演
    """
    
    def __init__(self):
        super().__init__()
        self.game_mode = "analysis"
        # 在推演模式下，不限制玩家颜色
        self.player_color = "B"  # 默认黑棋开始，但可以随时切换
        # 初始化局势演化存储系统
        self.evolution_storage = GameEvolutionMongoDB(f"analysis_{self.game_id}")
        
    def make_move(self, move):
        """
        推演模式下的落子方法
        允许用户自由落子，不触发AI回合
        """
        if move == "pass":
            # 处理过手
            self.moves.append((self.current_player, "pass"))
            
            # 添加胜率数据
            try:
                if not self.katago_initialized:
                    self._start_katago()
                analysis_result = self._send_analysis_request(max_visits=50)
                if analysis_result and 'rootInfo' in analysis_result:
                    winrate = analysis_result['rootInfo'].get('winrate', 0.5)
                    scoreMean = analysis_result['rootInfo'].get('scoreMean', 0)
                    self.winrate_history.append({
                        'move_number': len(self.moves),
                        'player': self.current_player,
                        'move': move,
                        'winrate': winrate,
                        'score_mean': scoreMean
                    })
                    
                    # 存储局势演化数据（过手）
                    try:
                        # 转换为黑白胜率
                        black_winrate = winrate * 100 if self.current_player == "B" else (1 - winrate) * 100
                        winrate_data = {
                            'black_winrate': black_winrate,
                            'white_winrate': 100 - black_winrate,
                            'score_lead': scoreMean
                        }
                        
                        # 获取推荐着法
                        recommended_moves = []
                        if 'moveInfos' in analysis_result:
                            for move_info in analysis_result['moveInfos'][:5]:
                                recommended_moves.append({
                                    'move': move_info.get('move', ''),
                                    'visits': move_info.get('visits', 0),
                                    'winrate': move_info.get('winrate', 0),
                                    'score_mean': move_info.get('scoreMean', 0)
                                })
                        
                        # 获取领地所有权数据
                        from ai_handler import AIHandler
                        ai_handler = AIHandler()
                        territory_ownership = ai_handler.get_territory_ownership(self)
                        
                        # 添加到局势演化存储
                        self.evolution_storage.add_move_data(
                            move_number=len(self.moves),
                            move="pass",
                            color=self.current_player,
                            board=self.board,
                            winrate_data=winrate_data,
                            recommended_moves=recommended_moves,
                            territory_ownership=territory_ownership
                        )
                        
                        # 保存到文件
                        self.evolution_storage.save_to_file()
                        
                    except Exception as storage_error:
                        print(f"推演模式过手局势演化数据存储失败: {storage_error}")
                        
            except Exception as e:
                print(f"推演模式胜率计算失败: {e}")
            
            # 切换玩家
            self.current_player = "W" if self.current_player == "B" else "B"
            return True
            
        # 解析坐标
        try:
            parsed_move = self.parse_move(move)
            if parsed_move in ["pass", "quit", None]:
                return False
            
            # 确保parsed_move是有效的字符串
            if not isinstance(parsed_move, str) or len(parsed_move) < 2:
                return False
            
            # 将字符串坐标转换为数字坐标
            col_char = parsed_move[0]
            row_str = parsed_move[1:]
            col_letters = "ABCDEFGHJKLMNOPQRST"
            col = col_letters.index(col_char)
            row = int(row_str) - 1
            print(f"坐标解析: {parsed_move} -> col_char='{col_char}', row_str='{row_str}'")
            print(f"坐标转换: {parsed_move} -> row={row}({type(row)}), col={col}({type(col)})")
            print(f"边界检查: 0 <= row({row}) < 19: {0 <= row < 19}, 0 <= col({col}) < 19: {0 <= col < 19}")
        except:
            return False
            
        # 检查是否为有效着法
        color_num = 1 if self.current_player == "B" else 2
        print(f"检查着法有效性: row={row}, col={col}, color_num={color_num}, current_player={self.current_player}")
        if not self.is_valid_move(row, col, color_num):
            print(f"无效的{self.current_player}棋着法: {parsed_move}")
            return False
        print(f"着法有效: {parsed_move}")
            
        # 保存当前棋盘状态（用于打劫检测）
        board_copy = [row[:] for row in self.board]
        self.board_history.append(board_copy)
        
        # 保存当前棋盘状态（用于打劫检测和自杀恢复）
        board_before = [row[:] for row in self.board]
        
        # 落子
        self.board[row][col] = color_num
        
        # 检查并移除被提取的棋子（使用正确的提子逻辑）
        opponent_color_num = 2 if self.current_player == "B" else 1
        captured_groups = []
        captured_count = 0
        
        # 只检查相邻的对方棋子组（正确的提子逻辑）
        for nr, nc in self.get_neighbors(row, col):
            if self.board[nr][nc] == opponent_color_num:
                group = self.get_group(nr, nc)
                if group and len(self.get_liberties(group)) == 0:
                    # 这个对方棋子组没有气，应该被提取
                    if group not in captured_groups:
                        captured_groups.append(group)
                        captured_count += len(group)
                        # 移除被提取的棋子
                        for gr, gc in group:
                            self.board[gr][gc] = 0
                            if opponent_color_num == 1:
                                self.captured_black += 1
                            else:
                                 self.captured_white += 1
        
        # 检查自杀：落子后自己的棋子组是否有气
        current_group = self.get_group(row, col)
        if len(self.get_liberties(current_group)) == 0:
            # 自杀，恢复棋盘状态
            self.board = board_before
            # 恢复被提取棋子的计数
            if opponent_color_num == 1:
                self.captured_black -= captured_count
            else:
                self.captured_white -= captured_count
            print(f"自杀着法: {move}")
            return False
        
        # 检测打劫
        self.ko_position = None
        if captured_count == 1 and len(captured_groups) == 1:
            if len(self.get_liberties(current_group)) == 1:
                # 这可能是打劫，记录被提取的位置
                captured_pos = next(iter(captured_groups[0]))
                self.ko_position = captured_pos
        
        # 记录棋盘历史
        self.board_history.append(board_before)
        if len(self.board_history) > 10:  # 只保留最近10步
            self.board_history.pop(0)
              
        # 记录着法
        self.moves.append((self.current_player, move))
        
        # 切换玩家（推演模式下允许自由切换）
        self.current_player = "W" if self.current_player == "B" else "B"
        
        # 添加胜率数据（在切换玩家后计算，因为KataGo返回的是当前要下棋玩家的胜率）
        try:
            if not self.katago_initialized:
                self._start_katago()
            analysis_result = self._send_analysis_request(max_visits=50)
            if analysis_result and 'rootInfo' in analysis_result:
                winrate = analysis_result['rootInfo'].get('winrate', 0.5)
                scoreLead = analysis_result['rootInfo'].get('scoreLead', 0)
                # 转换为黑棋胜率（KataGo返回的是当前要下棋玩家的胜率）
                black_winrate = winrate * 100 if self.current_player == "B" else (1 - winrate) * 100
                self.winrate_history.append({
                    'move_number': len(self.moves),
                    'player': self.moves[-1][0] if self.moves else 'B',  # 记录刚才落子的玩家
                    'move': move,
                    'black_winrate': black_winrate,
                    'score_lead': scoreLead
                })
                
                # 存储局势演化数据
                try:
                    # 获取当前胜率数据
                    winrate_data = {
                        'black_winrate': black_winrate,
                        'white_winrate': 100 - black_winrate,
                        'score_lead': scoreLead
                    }
                    
                    # 获取推荐着法
                    recommended_moves = []
                    if 'moveInfos' in analysis_result:
                        for move_info in analysis_result['moveInfos'][:5]:  # 取前5个推荐着法
                            recommended_moves.append({
                                'move': move_info.get('move', ''),
                                'visits': move_info.get('visits', 0),
                                'winrate': move_info.get('winrate', 0),
                                'score_mean': move_info.get('scoreMean', 0)
                            })
                    
                    # 获取领地所有权数据
                    territory_ownership = None
                    try:
                        analysis_result = self._send_analysis_request(max_visits=50)
                        if analysis_result and 'ownership' in analysis_result:
                            ownership_1d = analysis_result['ownership']
                            if len(ownership_1d) == 19 * 19:
                                territory_ownership = []
                                for row in range(19):
                                    row_data = []
                                    for col in range(19):
                                        index = row * 19 + col
                                        row_data.append(ownership_1d[index])
                                    territory_ownership.append(row_data)
                    except Exception as e:
                        print(f"获取领地数据失败: {e}")
                    
                    # 添加到局势演化存储
                    self.evolution_storage.add_move_data(
                        move_number=len(self.moves),
                        move=move,
                        color=self.moves[-1][0] if self.moves else 'B',
                        board=self.board,
                        winrate_data=winrate_data,
                        recommended_moves=recommended_moves,
                        territory_data=territory_ownership
                    )
                    
                    # 保存到文件
                    self.evolution_storage.save_to_file()
                    
                except Exception as storage_error:
                    print(f"推演模式局势演化数据存储失败: {storage_error}")
                    
        except Exception as e:
            print(f"推演模式胜率计算失败: {e}")
        
        return True
    
    def get_katago_move(self):
        """
        推演模式下禁用AI自动落子
        只返回分析结果，不实际落子
        """
        try:
            if not self.katago_initialized:
                self._start_katago()
            
            analysis_result = self._send_analysis_request(max_visits=200)
            if analysis_result and 'moveInfos' in analysis_result:
                # 返回分析结果但不落子
                return {
                    'type': 'analysis_only',
                    'analysis': analysis_result,
                    'message': '推演模式：AI仅提供分析，不自动落子'
                }
            else:
                return {
                    'type': 'error',
                    'message': '推演模式：AI分析失败'
                }
        except Exception as e:
            return {
                'type': 'error',
                'message': f'推演模式：AI分析错误 - {str(e)}'
            }
    
    def switch_current_player(self, color):
        """
        推演模式专用：手动切换当前玩家
        """
        if color in ["B", "W"]:
            self.current_player = color
            return True
        return False
    
    def is_analysis_mode(self):
        """
        标识这是推演模式
        """
        return True
    
    def load_from_sgf(self, sgf_content: str):
        """
        从SGF内容加载棋局（同步版本，用于兼容性）
        """
        import asyncio
        try:
            # 如果在异步环境中，创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.load_from_sgf_async(sgf_content))
        except RuntimeError:
            # 如果已经在事件循环中，直接调用异步版本但不使用回调
            return asyncio.create_task(self.load_from_sgf_async(sgf_content)).result()
        except:
            # 降级到简单的同步实现
            return self._load_from_sgf_sync(sgf_content)
    
    def _load_from_sgf_sync(self, sgf_content: str):
        """
        从SGF内容加载棋局（同步实现）
        """
        if sgf is None:
            print("SGF库未安装，无法解析SGF文件")
            return False
        
        try:
            # 解析SGF内容
            game_tree = sgf.Sgf_game.from_string(sgf_content)
            
            # 重置游戏状态
            self.reset_game()
            
            # 获取根节点
            root_node = game_tree.get_root()
            
            # 读取游戏信息
            try:
                board_size = root_node.get('SZ')
                if board_size is not None:
                    # 目前只支持19路棋盘
                    if board_size != 19:
                        print(f"不支持的棋盘大小: {board_size}x{board_size}，仅支持19x19")
                        return False
                else:
                    # 如果没有指定棋盘大小，默认为19路
                    print("SGF文件未指定棋盘大小，默认使用19x19")
            except (KeyError, AttributeError):
                # 如果SZ属性不存在或访问出错，默认为19路
                print("SGF文件未指定棋盘大小，默认使用19x19")
            
            # 读取贴目信息
            try:
                komi = root_node.get('KM')
                if komi is not None:
                    self.komi = float(komi)
            except (KeyError, AttributeError, ValueError):
                pass  # 使用默认贴目
            
            # 读取规则信息
            try:
                rules = root_node.get('RU')
                if rules:
                    # 简单的规则映射
                    if 'chinese' in rules.lower() or 'cn' in rules.lower():
                        self.rules = 'chinese'
                    elif 'japanese' in rules.lower() or 'jp' in rules.lower():
                        self.rules = 'japanese'
            except (KeyError, AttributeError):
                pass  # 使用默认规则
            
            # 遍历所有节点，加载着法
            move_count = 0
            
            # 获取主分支的所有节点
            main_sequence = game_tree.get_main_sequence()
            
            # 跳过根节点，从第二个节点开始处理着法
            for current_node in main_sequence[1:]:
                
                # 检查是否有黑棋着法
                try:
                    black_move = current_node.get('B')
                    if black_move is not None:
                        # 处理元组格式或字符串格式的坐标
                        if black_move == '' or (isinstance(black_move, tuple) and black_move == ()):
                            # 空字符串或空元组表示pass
                            move_str = 'pass'
                        else:
                            # 转换SGF坐标到我们的格式
                            move_str = self._sgf_to_move(black_move)
                        
                        if move_str:
                            self.current_player = 'B'
                            print(f"尝试黑棋着法: {move_str}")
                            success = self._sgf_make_move(move_str)
                            if not success:
                                print(f"跳过无效的黑棋着法: {move_str}")
                                continue
                            move_count += 1
                except (KeyError, AttributeError, TypeError):
                    pass  # 没有黑棋着法或类型错误
                
                # 检查是否有白棋着法
                try:
                    white_move = current_node.get('W')
                    if white_move is not None:
                        # 处理元组格式或字符串格式的坐标
                        if white_move == '' or (isinstance(white_move, tuple) and white_move == ()):
                            # 空字符串或空元组表示pass
                            move_str = 'pass'
                        else:
                            # 转换SGF坐标到我们的格式
                            move_str = self._sgf_to_move(white_move)
                        
                        if move_str:
                            self.current_player = 'W'
                            print(f"尝试白棋着法: {move_str}")
                            success = self._sgf_make_move(move_str)
                            if not success:
                                print(f"跳过无效的白棋着法: {move_str}")
                                continue
                            move_count += 1
                except (KeyError, AttributeError, TypeError):
                    pass  # 没有白棋着法或类型错误
            
            print(f"SGF文件加载成功，共加载了 {move_count} 手棋")
            return True
            
        except Exception as e:
            print(f"SGF解析失败: {e}")
            return False
    
    async def load_from_sgf_async(self, sgf_content: str, move_callback=None):
        """
        从SGF内容加载棋局
        """
        if sgf is None:
            print("SGF库未安装，无法解析SGF文件")
            return False
        
        try:
            # 解析SGF内容
            game_tree = sgf.Sgf_game.from_string(sgf_content)
            
            # 重置游戏状态
            self.reset_game()
            
            # 获取根节点
            root_node = game_tree.get_root()
            
            # 读取游戏信息
            try:
                board_size = root_node.get('SZ')
                if board_size is not None:
                    # 目前只支持19路棋盘
                    if board_size != 19:
                        print(f"不支持的棋盘大小: {board_size}x{board_size}，仅支持19x19")
                        return False
                else:
                    # 如果没有指定棋盘大小，默认为19路
                    print("SGF文件未指定棋盘大小，默认使用19x19")
            except (KeyError, AttributeError):
                # 如果SZ属性不存在或访问出错，默认为19路
                print("SGF文件未指定棋盘大小，默认使用19x19")
            
            # 读取贴目信息
            try:
                komi = root_node.get('KM')
                if komi is not None:
                    self.komi = float(komi)
            except (KeyError, AttributeError, ValueError):
                pass  # 使用默认贴目
            
            # 读取规则信息
            try:
                rules = root_node.get('RU')
                if rules:
                    # 简单的规则映射
                    if 'chinese' in rules.lower() or 'cn' in rules.lower():
                        self.rules = 'chinese'
                    elif 'japanese' in rules.lower() or 'jp' in rules.lower():
                        self.rules = 'japanese'
            except (KeyError, AttributeError):
                pass  # 使用默认规则
            
            # 遍历所有节点，加载着法
            move_count = 0
            
            # 获取主分支的所有节点
            main_sequence = game_tree.get_main_sequence()
            
            # 跳过根节点，从第二个节点开始处理着法
            for current_node in main_sequence[1:]:
                
                # 检查是否有黑棋着法
                try:
                    black_move = current_node.get('B')
                    if black_move is not None:
                        # 处理元组格式或字符串格式的坐标
                        if black_move == '' or (isinstance(black_move, tuple) and black_move == ()):
                            # 空字符串或空元组表示pass
                            move_str = 'pass'
                        else:
                            # 转换SGF坐标到我们的格式
                            move_str = self._sgf_to_move(black_move)
                        
                        if move_str:
                            self.current_player = 'B'
                            print(f"尝试黑棋着法: {move_str}")
                            success = self._sgf_make_move(move_str)
                            if not success:
                                print(f"跳过无效的黑棋着法: {move_str}")
                                continue
                            move_count += 1
                            # 调用回调函数发送棋盘状态更新
                            if move_callback:
                                await move_callback()
                except (KeyError, AttributeError, TypeError):
                    pass  # 没有黑棋着法或类型错误
                
                # 检查是否有白棋着法
                try:
                    white_move = current_node.get('W')
                    if white_move is not None:
                        # 处理元组格式或字符串格式的坐标
                        if white_move == '' or (isinstance(white_move, tuple) and white_move == ()):
                            # 空字符串或空元组表示pass
                            move_str = 'pass'
                        else:
                            # 转换SGF坐标到我们的格式
                            move_str = self._sgf_to_move(white_move)
                        
                        if move_str:
                            self.current_player = 'W'
                            print(f"尝试白棋着法: {move_str}")
                            success = self._sgf_make_move(move_str)
                            if not success:
                                print(f"跳过无效的白棋着法: {move_str}")
                                continue
                            move_count += 1
                            # 调用回调函数发送棋盘状态更新
                            if move_callback:
                                await move_callback()
                except (KeyError, AttributeError, TypeError):
                    pass  # 没有白棋着法或类型错误
            
            print(f"SGF文件加载成功，共加载了 {move_count} 手棋")
            return True
            
        except Exception as e:
            print(f"SGF解析失败: {e}")
            return False
    
    def _sgf_make_move(self, move):
        """
        SGF导入专用的落子方法
        正确处理提子逻辑：先执行提子，再落子，最后检查自杀
        """
        if move == "pass":
            # 处理过手
            self.moves.append((self.current_player, "pass"))
            self.current_player = "W" if self.current_player == "B" else "B"
            return True
            
        # 解析坐标
        try:
            parsed_move = self.parse_move(move)
            if parsed_move in ["pass", "quit", None]:
                return False
            
            # 确保parsed_move是有效的字符串
            if not isinstance(parsed_move, str) or len(parsed_move) < 2:
                return False
            
            # 将字符串坐标转换为数字坐标
            col_char = parsed_move[0]
            row_str = parsed_move[1:]
            col_letters = "ABCDEFGHJKLMNOPQRST"
            col = col_letters.index(col_char)
            row = int(row_str) - 1
        except:
            return False
            
        # 检查边界
        if not (0 <= row < 19 and 0 <= col < 19):
            return False
            
        color_num = 1 if self.current_player == "B" else 2
        opponent_color_num = 3 - color_num
        
        # 检查是否为同色棋子重复着法
        if self.board[row][col] == color_num:
            print(f"位置 {move} 已有同色棋子")
            return False
            
        # 保存当前棋盘状态
        board_before = [row[:] for row in self.board]
        
        # 先放置棋子（临时）
        self.board[row][col] = color_num
        
        # 检查并移除被提取的对方棋子
        captured_groups = []
        captured_count = 0
        
        # 检查相邻的对方棋子组
        for nr, nc in self.get_neighbors(row, col):
            if self.board[nr][nc] == opponent_color_num:
                group = self.get_group(nr, nc)
                if group and len(self.get_liberties(group)) == 0:
                    # 这个对方棋子组没有气，应该被提取
                    if group not in captured_groups:
                        captured_groups.append(group)
                        captured_count += len(group)
                        # 移除被提取的棋子
                        for gr, gc in group:
                            self.board[gr][gc] = 0
                            if opponent_color_num == 1:
                                self.captured_black += 1
                            else:
                                self.captured_white += 1
        
        # 检查自杀：落子后自己的棋子组是否有气
        current_group = self.get_group(row, col)
        if len(self.get_liberties(current_group)) == 0:
            # 自杀，恢复棋盘状态
            self.board = board_before
            # 恢复被提取棋子的计数
            if opponent_color_num == 1:
                self.captured_black -= captured_count
            else:
                self.captured_white -= captured_count
            print(f"自杀着法: {move}")
            return False
        
        # 检测打劫
        self.ko_position = None
        if captured_count == 1 and len(captured_groups) == 1:
            if len(self.get_liberties(current_group)) == 1:
                # 这可能是打劫，记录被提取的位置
                captured_pos = next(iter(captured_groups[0]))
                self.ko_position = captured_pos
        
        # 记录棋盘历史
        self.board_history.append(board_before)
        if len(self.board_history) > 10:  # 只保留最近10步
            self.board_history.pop(0)
        
        # 记录着法
        self.moves.append((self.current_player, move))
        
        # 记录胜率历史（在切换玩家之前获取当前局面的分析）
        try:
            if hasattr(self, 'katago_initialized') and self.katago_initialized:
                analysis_result = self._send_analysis_request(max_visits=50)  # 使用较少访问次数以提高速度
                move_infos = analysis_result.get("moveInfos", [])
                if move_infos:
                    best_move = move_infos[0]
                    winrate = best_move.get("winrate", 0.5)
                    score_lead = best_move.get("scoreLead", 0)
                    
                    # KataGo配置reportAnalysisWinratesAs = SIDETOMOVE
                    # 分析的是落子后的局面，此时轮到对方下棋
                    # 所以返回的胜率是对方（即将下棋方）的胜率
                    next_player = "W" if self.current_player == "B" else "B"
                    if next_player == "B":
                        # 下一步是黑棋回合，KataGo返回的是黑棋胜率
                        black_winrate = winrate * 100
                    else:
                        # 下一步是白棋回合，KataGo返回的是白棋胜率，需要转换为黑棋胜率
                        black_winrate = (1 - winrate) * 100
                    
                    white_winrate = 100 - black_winrate
                    
                    winrate_data = {
                        "move_number": len(self.moves),
                        "move": move,
                        "color": self.current_player,
                        "black_winrate": round(black_winrate, 1),
                        "white_winrate": round(white_winrate, 1),
                        "score_lead": round(score_lead, 1)
                    }
                    self.winrate_history.append(winrate_data)
                    print(f"SGF胜率记录: 黑棋{black_winrate:.1f}% 白棋{white_winrate:.1f}%")
        except Exception as e:
            print(f"SGF胜率计算失败: {e}")
        
        # 切换玩家
        self.current_player = "W" if self.current_player == "B" else "B"
        
        print(f"SGF着法成功: {move}, 提取了 {captured_count} 个对方棋子")
        return True
    
    def _sgf_to_move(self, sgf_coord):
        """
        将SGF坐标转换为我们的着法格式
        SGF使用aa-ss的格式或(x,y)元组格式，我们使用A1-T19的格式
        """
        # 处理元组格式的坐标 (x, y)
        if isinstance(sgf_coord, tuple) and len(sgf_coord) == 2:
            col_index, row_index = sgf_coord
            print(f"处理元组坐标: {sgf_coord} -> col_index={col_index}, row_index={row_index}")
            # 我们的列坐标从A开始（跳过I）
            our_cols = 'ABCDEFGHJKLMNOPQRST'
            
            try:
                # 检查坐标范围：SGF坐标从0开始，19路棋盘范围是0-18
                if 0 <= col_index < 19 and 0 <= row_index < 19:
                    our_col = our_cols[col_index]
                    # SGF坐标系统：(0,0)是左上角，(18,18)是右下角
                    # 我们的坐标系统：A1是左下角，T19是右上角
                    # 所以行坐标需要翻转：SGF的row_index=0对应我们的19，row_index=18对应我们的1
                    our_row = 19 - row_index
                    result = f"{our_col}{our_row}"
                    print(f"转换结果: {result}")
                    return result
                else:
                    print(f"坐标超出范围: col_index={col_index}, row_index={row_index}")
                    return None
            except (ValueError, IndexError) as e:
                print(f"转换异常: {e}")
                return None
        
        # 处理字符串格式的坐标
        if not isinstance(sgf_coord, str):
            # 如果是字节类型，尝试解码
            if isinstance(sgf_coord, bytes):
                try:
                    sgf_coord = sgf_coord.decode('utf-8')
                except UnicodeDecodeError:
                    return None
            # 如果是其他类型，尝试转换为字符串
            else:
                try:
                    sgf_coord = str(sgf_coord)
                except:
                    return None
        
        if len(sgf_coord) != 2:
            return None
        
        col_char = sgf_coord[0]
        row_char = sgf_coord[1]
        
        # SGF的坐标从a开始，我们的从A开始（跳过I）
        sgf_cols = 'abcdefghijklmnopqrs'
        our_cols = 'ABCDEFGHJKLMNOPQRST'
        
        try:
            col_index = sgf_cols.index(col_char)
            our_col = our_cols[col_index]
            
            # SGF的行坐标从a开始（对应19），我们的从1开始
            row_index = sgf_cols.index(row_char)
            our_row = 19 - row_index
            
            return f"{our_col}{our_row}"
        except (ValueError, IndexError):
            return None
    
    def reset_game(self):
        """
        重置游戏到初始状态
        """
        # 重置棋盘
        self.board = [[0 for _ in range(19)] for _ in range(19)]
        
        # 重置游戏状态
        self.moves = []
        self.current_player = "B"
        self.captured_black = 0
        self.captured_white = 0
        self.board_history = []
        self.winrate_history = []
        
        # 保持游戏设置不变（贴目、规则等）
        print("游戏状态已重置")