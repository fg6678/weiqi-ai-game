import json, subprocess, threading, queue, os, sys, time
from storage.game_evolution_mongodb import GameEvolutionMongoDB
from datetime import datetime

MODEL = "/Volumes/exdata/katago/models/kata1-b28c512nbt-s10063600896-d5087116207.bin.gz"
CFG   = "/Volumes/exdata/projects/weiqitest/analysis.cfg"
KATAGO_BIN = "katago"

class WeiQiGame:
    def __init__(self):
        # 生成唯一的游戏ID
        self.game_id = f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.board_size = 19
        self.moves = []
        self.current_player = "B"
        self.game_over = False
        self.proc = None
        # 棋盘状态：0=空，1=黑棋，2=白棋
        self.board = [[0 for _ in range(19)] for _ in range(19)]
        self.captured_black = 0  # 被提取的黑子数
        self.captured_white = 0  # 被提取的白子数
        
        # 游戏设置
        self.player_color = "B"  # 玩家执子颜色
        self.ai_time_limit = 3   # AI思考时间（秒）
        self.komi = 6.5          # 贴目
        self.rules = "chinese"   # 规则
        
        # 打劫相关
        self.ko_position = None  # 打劫位置 (row, col)
        self.board_history = []  # 棋盘历史状态，用于检测打劫
        
        # KataGo相关
        self.katago_initialized = False
        self.out_q = None
        self.stderr_q = None
        
        # 实时分析相关
        self.realtime_analysis_active = False
        self.realtime_thread = None
        self.suggestion_ai_time_limit = 10  # 推荐选点AI的固定算力（秒）
        
        # 胜率历史数据
        self.winrate_history = []  # 存储每步的胜率和目数信息
        
        # 局势演化存储系统
        self.evolution_storage = GameEvolutionMongoDB(self.game_id)

    def _add_initial_winrate(self):
        """添加游戏开始时的初始胜率数据"""
        try:
            # 延迟初始化，在第一次需要时启动KataGo
            if not self.katago_initialized:
                self._start_katago()
            
            # 获取初始局面的胜率
            analysis_result = self._send_analysis_request(max_visits=50)
            move_infos = analysis_result.get("moveInfos", [])
            if move_infos:
                best_move = move_infos[0]
                winrate = best_move.get("winrate", 0.5)
                score_lead = best_move.get("scoreLead", 0)
                
                # 初始局面，黑棋先行，KataGo返回的是黑棋胜率
                black_winrate = winrate * 100
                white_winrate = 100 - black_winrate
                
                initial_data = {
                    "move_number": 0,
                    "move": "开局",
                    "color": "B",
                    "black_winrate": round(black_winrate, 1),
                    "white_winrate": round(white_winrate, 1),
                    "score_lead": round(score_lead, 1)
                }
                self.winrate_history.append(initial_data)
        except Exception as e:
            print(f"添加初始胜率数据失败: {e}")
            # 如果失败，添加默认数据
            default_data = {
                "move_number": 0,
                "move": "开局",
                "color": "B",
                "black_winrate": 50.0,
                "white_winrate": 50.0,
                "score_lead": 0.0
            }
            self.winrate_history.append(default_data)

    def _start_katago(self):
        if self.katago_initialized:
            return
            
        if not os.path.exists(MODEL):
            raise RuntimeError(f"模型文件不存在: {MODEL}")
        if not os.path.exists(CFG):
            raise RuntimeError(f"配置文件不存在: {CFG}")

        print("正在启动 KataGo...")
        print(f"模型文件: {MODEL}")
        print(f"配置文件: {CFG}")
        print(f"玩家颜色: {self.player_color}")

        try:
            version_result = subprocess.run(
                [KATAGO_BIN, "version"],
                capture_output=True, text=True, timeout=10
            )
            if version_result.returncode == 0:
                print(f"KataGo 版本: {version_result.stdout.strip()}")
            else:
                print(f"KataGo 版本检查失败: {version_result.stderr}")
        except Exception as e:
            print(f"无法获取 KataGo 版本: {e}")

        self.proc = subprocess.Popen(
            [KATAGO_BIN, "analysis", "-model", MODEL, "-config", CFG],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1
        )

        time.sleep(2)
        if self.proc.poll() is not None:
            stderr_output = self.proc.stderr.read()
            raise RuntimeError(f"KataGo 启动失败，退出码: {self.proc.returncode}\n错误信息: {stderr_output}")

        # 初始化队列和线程
        self.out_q = queue.Queue()
        self.stderr_q = queue.Queue()
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._stderr_reader, daemon=True).start()
        
        self.katago_initialized = True
        print("KataGo 启动成功！")

    def _stderr_reader(self):
        try:
            for line in self.proc.stderr:
                line = line.strip()
                if line:
                    if "Unexpected or unused field" not in line:
                        print(f"KataGo stderr: {line}", file=sys.stderr)
        except Exception as e:
            print(f"读取 KataGo 错误输出时出错: {e}", file=sys.stderr)

    def _check_process_alive(self):
        if self.proc is None or self.proc.poll() is not None:
            if self.proc and self.proc.poll() is not None:
                print(f"KataGo 进程已终止，退出码: {self.proc.poll()}")
                while not self.stderr_q.empty():
                    try:
                        stderr_line = self.stderr_q.get_nowait()
                        print(f"KataGo 错误: {stderr_line}")
                    except queue.Empty:
                        break
            return False
        return True

    def _reader(self):
        try:
            for line in self.proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    self.out_q.put(json.loads(line))
                except json.JSONDecodeError:
                    print("Non-JSON:", line, file=sys.stderr)
        except Exception as e:
            print(f"读取 KataGo 输出时出错: {e}", file=sys.stderr)

    def _send_analysis_request(self, max_visits=200):
        if not self._check_process_alive():
            raise RuntimeError("KataGo 进程已终止")

        req = {
            "id": f"move_{len(self.moves)}",
            "rules": "Chinese",
            "komi": self.komi,
            "boardXSize": self.board_size,
            "boardYSize": self.board_size,
            "moves": self.moves.copy(),
            "maxVisits": int(max_visits),
            "includeOwnership": True
        }

        try:
            request_json = json.dumps(req)
            print(f"发送分析请求: {request_json}")
            self.proc.stdin.write(request_json + "\n")
            self.proc.stdin.flush()
        except BrokenPipeError:
            raise RuntimeError("无法向 KataGo 发送请求，进程可能已终止")

        timeout_count = 0
        while timeout_count < 200:  # 最多等待20秒
            try:
                msg = self.out_q.get(timeout=0.1)
                print(f"收到 KataGo 响应: {json.dumps(msg, ensure_ascii=False)}")
                # KataGo 分析完成的标志是 isDuringSearch 为 false
                if not msg.get("isDuringSearch", True):
                    return msg
            except queue.Empty:
                timeout_count += 1
                if timeout_count % 50 == 0:  # 每5秒打印一次等待信息
                    print(f"等待 KataGo 响应中... ({timeout_count/10:.1f}秒)")
                if not self._check_process_alive():
                    raise RuntimeError("KataGo 进程在分析过程中终止")
                continue

        raise RuntimeError("KataGo 分析超时")
    
    def start_realtime_analysis(self, callback_func, max_visits=None):
        """开始实时分析，持续获取推荐选点"""
        if not self._check_process_alive():
            raise RuntimeError("KataGo 进程已终止")
        
        # 停止之前的分析
        self.stop_realtime_analysis()
        
        # 使用独立的推荐选点AI算力设置
        if max_visits is None:
            max_visits = max(1, int(self.suggestion_ai_time_limit * 100))  # 推荐选点专用算力，确保为正整数
        
        req = {
            "id": f"realtime_{len(self.moves)}_{int(time.time())}",
            "rules": "Chinese",
            "komi": self.komi,
            "boardXSize": self.board_size,
            "boardYSize": self.board_size,
            "moves": self.moves.copy(),
            "maxVisits": int(max_visits),
            "includeOwnership": True,
            "reportDuringSearchEvery": 0.5  # 每0.5秒报告一次进度
        }
        
        try:
            request_json = json.dumps(req)
            print(f"发送实时分析请求: {request_json}")
            self.proc.stdin.write(request_json + "\n")
            self.proc.stdin.flush()
            
            # 启动实时分析线程
            self.realtime_analysis_active = True
            self.realtime_thread = threading.Thread(
                target=self._realtime_analysis_worker, 
                args=(callback_func, req["id"])
            )
            self.realtime_thread.daemon = True
            self.realtime_thread.start()
            
        except BrokenPipeError:
            raise RuntimeError("无法向 KataGo 发送实时分析请求，进程可能已终止")
    
    def _realtime_analysis_worker(self, callback_func, request_id):
        """实时分析工作线程"""
        try:
            while self.realtime_analysis_active:
                try:
                    msg = self.out_q.get(timeout=0.1)
                    
                    # 检查是否是我们的请求的响应
                    if msg.get("id") == request_id:
                        move_infos = msg.get("moveInfos", [])
                        if move_infos:
                            # 提取推荐选点数据
                            suggestions = []
                            for mv in move_infos[:7]:  # 最多7个推荐
                                suggestions.append({
                                    "move": mv["move"],
                                    "winrate": mv["winrate"],
                                    "score_lead": mv.get("scoreLead", 0),
                                    "visits": mv.get("visits", 0)
                                })
                            
                            # 调用回调函数更新前端
                            callback_func(suggestions)
                        
                        # 如果分析完成，停止实时分析
                        if not msg.get("isDuringSearch", True):
                            print("实时分析完成")
                            break
                            
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"实时分析工作线程错误: {e}")
                    break
                    
        except Exception as e:
            print(f"实时分析线程异常: {e}")
        finally:
            self.realtime_analysis_active = False
    
    def stop_realtime_analysis(self):
        """停止实时分析"""
        if hasattr(self, 'realtime_analysis_active'):
            self.realtime_analysis_active = False
        if hasattr(self, 'realtime_thread') and self.realtime_thread and self.realtime_thread.is_alive():
            self.realtime_thread.join(timeout=1.0)

    def get_katago_move(self):
        # 确保KataGo已启动
        if not self.katago_initialized:
            self._start_katago()
            
        try:
            # 对手AI使用用户设置的算力
            max_visits = int(self.ai_time_limit * 100)  # 根据时间限制计算访问次数，确保为整数
            result = self._send_analysis_request(max_visits=max_visits)
            move_infos = result.get("moveInfos", [])

            if not move_infos:
                return "pass"

            print("\n=== KataGo 推荐着法 ===")
            for i, mv in enumerate(move_infos[:3], 1):
                print(f"{i}. {mv['move']} (胜率: {mv['winrate']*100:.1f}%, 得分: {mv.get('scoreLead', 0):.1f})")

            return move_infos[0]["move"]
        except Exception as e:
            print(f"获取 KataGo 着法时出错: {e}")
            return "pass"

    def display_board(self):
        print("\n=== 当前棋盘 ===")
        print(f"已下 {len(self.moves)} 手，轮到 {'黑棋' if self.current_player == 'B' else '白棋'}")

        if self.moves:
            print("最近着法:")
            for i, move in enumerate(self.moves[-5:], len(self.moves)-len(self.moves[-5:])+1):
                color_char, position = move
                color = "黑" if color_char == "B" else "白"
                print(f"  {i}. {color}: {position}")
        else:
            print("空棋盘")

    def parse_move(self, move_str):
        move_str = move_str.strip().upper()
        if move_str in ["PASS", "P", "过"]:
            return "pass"
        if move_str in ["QUIT", "Q", "退出", "结束"]:
            return "quit"
        if len(move_str) >= 2:
            col_char = move_str[0]
            row_str = move_str[1:]
            try:
                if 'A' <= col_char <= 'T':
                    col = ord(col_char) - ord('A')
                    if col_char >= 'I':
                        col -= 1
                    row = int(row_str) - 1
                    if 0 <= col < 19 and 0 <= row < 19:
                        col_letters = "ABCDEFGHJKLMNOPQRST"
                        return f"{col_letters[col]}{row + 1}"
            except ValueError:
                pass
        return None

    def get_neighbors(self, row, col):
        """获取相邻位置"""
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if 0 <= nr < 19 and 0 <= nc < 19:
                neighbors.append((nr, nc))
        return neighbors
    
    def get_group(self, row, col):
        """获取连通的棋子组"""
        if self.board[row][col] == 0:
            return set()
        
        color = self.board[row][col]
        group = set()
        stack = [(row, col)]
        
        while stack:
            r, c = stack.pop()
            if (r, c) in group:
                continue
            group.add((r, c))
            
            for nr, nc in self.get_neighbors(r, c):
                if self.board[nr][nc] == color and (nr, nc) not in group:
                    stack.append((nr, nc))
        
        return group
    
    def get_liberties(self, group):
        """获取棋子组的气"""
        liberties = set()
        for row, col in group:
            for nr, nc in self.get_neighbors(row, col):
                if self.board[nr][nc] == 0:
                    liberties.add((nr, nc))
        return liberties
    
    def remove_captured_groups(self, opponent_color):
        """移除被提取的对方棋子组"""
        captured_stones = []
        
        for row in range(19):
            for col in range(19):
                if self.board[row][col] == opponent_color:
                    group = self.get_group(row, col)
                    if group and len(self.get_liberties(group)) == 0:
                        # 这个组没有气，被提取
                        for r, c in group:
                            self.board[r][c] = 0
                            captured_stones.append((r, c))
                        
                        if opponent_color == 1:
                            self.captured_black += len(group)
                        else:
                            self.captured_white += len(group)
        
        return captured_stones
    
    def get_captured_groups(self, opponent_color):
        """获取被提取的对方棋子组（不实际移除）"""
        captured_groups = []
        visited = set()
        
        for row in range(19):
            for col in range(19):
                if (row, col) not in visited and self.board[row][col] == opponent_color:
                    group = self.get_group(row, col)
                    if group and len(self.get_liberties(group)) == 0:
                        # 这个组没有气，被提取
                        captured_groups.append(group)
                        visited.update(group)
        
        return captured_groups
    
    def is_valid_move(self, row, col, color):
        """检查着法是否合法（考虑提子逻辑）"""
        print(f"is_valid_move调试: row={row}, col={col}, color={color}")
        print(f"棋盘位置状态: self.board[{row}][{col}] = {self.board[row][col]}")
        
        # 创建棋盘副本进行模拟
        board_copy = [row[:] for row in self.board]
        
        # 如果位置被占用，检查是否是同色棋子
        if board_copy[row][col] != 0:
            if board_copy[row][col] == color:
                print(f"同色棋子重复着法，无效: {color}")
                return False
            print(f"位置被对方棋子占用: {board_copy[row][col]}，检查是否能通过提子解决")
        
        # 在副本上放置棋子
        board_copy[row][col] = color
        
        # 检查并移除被提取的对方棋子
        opponent_color = 3 - color  # 1->2, 2->1
        captured_any = False
        
        neighbors = self.get_neighbors(row, col)
        for nr, nc in neighbors:
            if board_copy[nr][nc] == opponent_color:
                group = self._get_group_on_board(board_copy, nr, nc)
                liberties = self._get_liberties_on_board(board_copy, group)
                print(f"对方棋子组 ({nr},{nc}): group={len(group)}, liberties={len(liberties)}")
                if group and len(liberties) == 0:
                    # 在副本上移除被提取的棋子
                    for gr, gc in group:
                        board_copy[gr][gc] = 0
                    captured_any = True
                    print(f"可以提取对方棋子组: {group}")
        
        # 检查自己的棋子组是否有气
        own_group = self._get_group_on_board(board_copy, row, col)
        own_liberties = self._get_liberties_on_board(board_copy, own_group)
        own_liberties_count = len(own_liberties)
        print(f"自己的棋子组: group={len(own_group)}, liberties={own_liberties_count}")
        
        result = own_liberties_count > 0
        print(f"着法有效性结果: own_liberties={own_liberties_count}, result={result}")
        
        return result
    
    def _get_group_on_board(self, board, row, col):
        """在指定棋盘上获取棋子组"""
        if board[row][col] == 0:
            return set()
        
        color = board[row][col]
        group = set()
        stack = [(row, col)]
        
        while stack:
            r, c = stack.pop()
            if (r, c) in group:
                continue
            group.add((r, c))
            
            for nr, nc in self.get_neighbors(r, c):
                if board[nr][nc] == color and (nr, nc) not in group:
                    stack.append((nr, nc))
        
        return group
    
    def _get_liberties_on_board(self, board, group):
        """在指定棋盘上获取棋子组的气"""
        liberties = set()
        for r, c in group:
            for nr, nc in self.get_neighbors(r, c):
                if board[nr][nc] == 0:
                    liberties.add((nr, nc))
        return liberties
    
    def make_move(self, move):
        if move == "pass":
            self.moves.append([self.current_player, move])
            self.current_player = "W" if self.current_player == "B" else "B"
            self.ko_position = None  # 清除打劫状态
            return True
        
        # 解析坐标
        if len(move) < 2:
            return False
        
        col_char = move[0]
        row_str = move[1:]
        col_letters = 'ABCDEFGHJKLMNOPQRST'
        
        if col_char not in col_letters:
            return False
        
        try:
            col = col_letters.index(col_char)
            row = int(row_str) - 1
        except (ValueError, IndexError):
            return False
        
        if not (0 <= row < 19 and 0 <= col < 19):
            return False
        
        color = 1 if self.current_player == "B" else 2
        
        # 检查打劫规则
        if self.ko_position and (row, col) == self.ko_position:
            return False  # 不能立即回提
        
        # 检查着法是否合法
        if not self.is_valid_move(row, col, color):
            return False
        
        # 保存当前棋盘状态
        board_before = [row[:] for row in self.board]
        
        # 放置棋子
        self.board[row][col] = color
        
        # 移除被提取的对方棋子
        opponent_color = 3 - color
        captured_groups = self.get_captured_groups(opponent_color)
        captured_count = 0
        
        for group in captured_groups:
            captured_count += len(group)
            for r, c in group:
                self.board[r][c] = 0
                if opponent_color == 1:
                    self.captured_black += 1
                else:
                    self.captured_white += 1
        
        # 检测打劫：如果只提取了一个子，且当前棋子只有一口气，可能是打劫
        self.ko_position = None
        if captured_count == 1 and len(captured_groups) == 1:
            current_group = self.get_group(row, col)
            if len(self.get_liberties(current_group)) == 1:
                # 这可能是打劫，记录被提取的位置
                captured_pos = next(iter(captured_groups[0]))
                self.ko_position = captured_pos
        
        # 记录棋盘历史
        self.board_history.append(board_before)
        if len(self.board_history) > 10:  # 只保留最近10步
            self.board_history.pop(0)
        
        # 记录着法
        # 如果在分支模式下（有move_count属性且小于总着法数），在当前位置插入新着法
        if hasattr(self, 'move_count') and self.move_count < len(self.moves):
            # 截断后续着法，从当前位置开始新的分支
            self.moves = self.moves[:self.move_count]
            # 同时截断胜率历史，避免数据不一致
            if hasattr(self, 'winrate_history'):
                self.winrate_history = self.winrate_history[:self.move_count]
            self.moves.append([self.current_player, move])
            self.move_count = len(self.moves)
        else:
            # 正常模式，直接追加
            self.moves.append([self.current_player, move])
            if hasattr(self, 'move_count'):
                self.move_count = len(self.moves)
        
        # 记录胜率历史（在切换玩家之前获取当前局面的分析）
        # 在分支模式下跳过胜率分析以提高响应速度
        is_branch_mode = hasattr(self, 'move_count') and self.move_count < len(self.moves) - 1
        
        try:
            if self.katago_initialized and not is_branch_mode:
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
            elif is_branch_mode:
                # 分支模式下，添加一个简单的胜率记录以保持数据结构一致
                winrate_data = {
                    "move_number": len(self.moves),
                    "move": move,
                    "color": self.current_player,
                    "black_winrate": 50.0,  # 默认值
                    "white_winrate": 50.0,  # 默认值
                    "score_lead": 0.0
                }
                self.winrate_history.append(winrate_data)
        except Exception as e:
            print(f"记录胜率历史失败: {e}")
        
        # 存储局势演化数据
        try:
            print(f"[DEBUG] 开始存储局势演化数据，当前手数: {len(self.moves)}")
            
            # 获取当前的胜率数据
            current_winrate_data = {
                "black_winrate": 50.0,
                "white_winrate": 50.0,
                "score_lead": 0.0
            }
            
            if self.winrate_history:
                latest_winrate = self.winrate_history[-1]
                current_winrate_data = {
                    "black_winrate": latest_winrate.get("black_winrate", 50.0),
                    "white_winrate": latest_winrate.get("white_winrate", 50.0),
                    "score_lead": latest_winrate.get("score_lead", 0.0)
                }
            
            # 获取推荐着法（如果有实时分析）
            recommended_moves = []
            if self.katago_initialized and not is_branch_mode:
                try:
                    analysis_result = self._send_analysis_request(max_visits=100)
                    move_infos = analysis_result.get("moveInfos", [])
                    for i, move_info in enumerate(move_infos[:5]):  # 取前5个推荐着法
                        recommended_moves.append({
                            "rank": i + 1,
                            "move": move_info.get("move", ""),
                            "winrate": move_info.get("winrate", 0.5),
                            "visits": move_info.get("visits", 0),
                            "score_lead": move_info.get("scoreLead", 0)
                        })
                except Exception as e:
                    print(f"获取推荐着法失败: {e}")
            
            # 获取领地所有权数据（如果可用）
            ownership_data = None
            if self.katago_initialized and not is_branch_mode:
                try:
                    analysis_result = self._send_analysis_request(max_visits=50)
                    if 'ownership' in analysis_result:
                        ownership_1d = analysis_result['ownership']
                        if len(ownership_1d) == 19 * 19:
                            ownership_data = []
                            for row in range(19):
                                row_data = []
                                for col in range(19):
                                    index = row * 19 + col
                                    row_data.append(ownership_1d[index])
                                ownership_data.append(row_data)
                except Exception as e:
                    print(f"获取领地数据失败: {e}")
            
            # 添加局势演化数据
            color_name = "black" if self.current_player == "B" else "white"
            print(f"[DEBUG] 准备添加局势演化数据: move={move}, color={color_name}")
            
            self.evolution_storage.add_move_data(
                move_number=len(self.moves),
                move=move,
                color=color_name,
                board=self.board,
                winrate_data=current_winrate_data,
                recommended_moves=recommended_moves,
                territory_data=ownership_data
            )
            print(f"[DEBUG] 局势演化数据已添加")
            
            # 保存到文件
            print(f"[DEBUG] 准备保存到文件: {self.evolution_storage.storage_path}")
            self.evolution_storage.save_to_file()
            print(f"[DEBUG] 文件保存完成")
            
        except Exception as e:
            print(f"存储局势演化数据失败: {e}")
            import traceback
            traceback.print_exc()
        
        self.current_player = "W" if self.current_player == "B" else "B"
        
        return True

    def play(self):
        print("=== 围棋人机对弈 ===")
        print("输入格式: D4, Q16 等 (列用A-T，行用1-19)")
        print("特殊命令: pass/p (过), quit/q (退出)")
        print("你执黑棋先行！\n")

        while not self.game_over:
            self.display_board()
            if self.current_player == "B":
                while True:
                    user_input = input("\n请输入你的着法: ").strip()
                    move = self.parse_move(user_input)
                    if move == "quit":
                        print("游戏结束！")
                        self.game_over = True
                        break
                    elif move is None:
                        print("无效输入！请使用格式如 D4, Q16 或输入 pass")
                        continue
                    else:
                        print(f"你下了: {move}")
                        self.make_move(move)
                        break
            else:
                print("\nKataGo 思考中...")
                katago_move = self.get_katago_move()
                print(f"KataGo 下了: {katago_move}")
                self.make_move(katago_move)

            if len(self.moves) >= 2:
                if self.moves[-1][1] == "pass" and self.moves[-2][1] == "pass":
                    print("\n双方都选择过，游戏结束！")
                    self.game_over = True

    def undo_move(self):
        """悔棋：撤销最后一步着法"""
        return self.undo_last_move()
    
    def undo_last_move(self):
        """悔棋：撤销最后一步着法"""
        if len(self.moves) == 0:
            return False
        
        # 获取最后一步着法
        last_move = self.moves.pop()
        last_player, last_position = last_move
        
        # 如果是pass，只需要切换玩家
        if last_position == "pass":
            self.current_player = last_player
            return True
        
        # 解析坐标
        col_char = last_position[0]
        row_str = last_position[1:]
        col_letters = 'ABCDEFGHJKLMNOPQRST'
        
        try:
            col = col_letters.index(col_char)
            row = int(row_str) - 1
        except (ValueError, IndexError):
            # 如果解析失败，恢复moves
            self.moves.append(last_move)
            return False
        
        # 移除棋子
        self.board[row][col] = 0
        
        # 切换回上一个玩家
        self.current_player = last_player
        
        # 注意：这里简化处理，没有恢复被提取的棋子
        # 在实际应用中，可能需要保存更多的游戏状态信息
        
        return True
    
    def goto_move(self, move_index):
        """回溯到指定着法，删除后续所有着法"""
        if move_index < 0 or move_index > len(self.moves):
            return False
        
        try:
            # 保存要保留的着法
            moves_to_keep = self.moves[:move_index]
            
            # 重置游戏状态
            self.board = [[0 for _ in range(19)] for _ in range(19)]
            self.current_player = "B"
            self.captured_black = 0
            self.captured_white = 0
            self.moves = []
            
            # 重新执行保留的着法
            for move in moves_to_keep:
                success = self.make_move(move[1])
                if not success:
                    return False
            
            # 清除胜率历史中超出当前手数的数据
            if hasattr(self, 'winrate_history'):
                self.winrate_history = [wr for wr in self.winrate_history if wr.get('move_number', 0) <= move_index]
            
            return True
        except Exception as e:
            print(f"回溯失败: {e}")
            return False

    def change_player_color(self, color):
        """修改玩家执子颜色"""
        if color in ["B", "W"]:
            self.player_color = color
            return True
        return False
    
    def change_ai_strength(self, time_limit):
        """修改AI算力（思考时间）"""
        if isinstance(time_limit, (int, float)) and time_limit > 0:
            self.ai_time_limit = time_limit
            return True
        return False
    
    def change_komi(self, komi):
        """修改贴目"""
        if isinstance(komi, (int, float)):
            self.komi = komi
            return True
        return False
    
    def change_rules(self, rules):
        """修改规则"""
        if rules in ["chinese", "japanese", "korean"]:
            self.rules = rules
            return True
        return False
    
    def change_suggestion_ai_strength(self, strength):
        """更改推荐选点AI算力"""
        try:
            strength_int = int(strength)
            if 1 <= strength_int <= 10:
                self.suggestion_ai_time_limit = strength_int
                return True
        except (ValueError, TypeError):
            pass
        return False

    def cleanup(self):
        # 停止实时分析
        self.stop_realtime_analysis()
        
        if self.proc:
            try:
                self.proc.stdin.close()
            except:
                pass
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()

if __name__ == "__main__":
    try:
        game = WeiQiGame()
        game.play()
    except RuntimeError as e:
        print(f"错误: {e}")
    except KeyboardInterrupt:
        print("\n游戏被中断！")
    finally:
        if 'game' in locals():
            game.cleanup()
        print("再见！")