import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import copy

class GameEvolutionStorage:
    """对局局势演化存储系统
    
    负责存储和管理每步棋的详细数据，包括：
    - 胜率和目差
    - 棋块编号和分析
    - 领地预测坐标
    - 已落子数组
    - 推荐落点数据
    """
    
    def __init__(self, game_id: str = None):
        self.game_id = game_id or self._generate_game_id()
        self.evolution_data = []
        self.storage_path = f"game_evolution_{self.game_id}.json"
        
        # 初始化空局面数据
        self._add_initial_state()
    
    def _generate_game_id(self) -> str:
        """生成唯一的游戏ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"game_{timestamp}"
    
    def _add_initial_state(self):
        """添加游戏开始时的初始状态"""
        initial_state = {
            "move_number": 0,
            "move": "game_start",
            "color": None,
            "timestamp": datetime.now().isoformat(),
            "winrate_data": {
                "black_winrate": 50.0,
                "white_winrate": 50.0,
                "score_lead": 0.0
            },
            "stone_groups": [],
            "territory_prediction": {},
            "placed_stones": [],
            "recommended_moves": []
        }
        self.evolution_data.append(initial_state)
    
    def analyze_stone_groups(self, board: List[List[int]]) -> List[Dict]:
        """分析棋盘上的所有棋块
        
        Args:
            board: 19x19的棋盘数组，0=空，1=黑棋，2=白棋
            
        Returns:
            棋块信息列表，每个棋块包含编号、颜色、坐标等信息
        """
        visited = [[False for _ in range(19)] for _ in range(19)]
        groups = []
        group_id = 1
        
        for row in range(19):
            for col in range(19):
                if board[row][col] != 0 and not visited[row][col]:
                    # 发现新的棋块，进行深度优先搜索
                    group_stones = []
                    color = board[row][col]
                    self._dfs_group(board, visited, row, col, color, group_stones)
                    
                    if group_stones:
                        # 计算棋块的气数
                        liberties = self._calculate_liberties(board, group_stones)
                        
                        group_info = {
                            "group_id": group_id,
                            "color": "black" if color == 1 else "white",
                            "stones": group_stones,
                            "stone_count": len(group_stones),
                            "liberties": len(liberties),
                            "liberty_positions": liberties
                        }
                        groups.append(group_info)
                        group_id += 1
        
        return groups
    
    def _dfs_group(self, board: List[List[int]], visited: List[List[bool]], 
                   row: int, col: int, color: int, group_stones: List[Tuple[int, int]]):
        """深度优先搜索连通的棋块"""
        if (row < 0 or row >= 19 or col < 0 or col >= 19 or 
            visited[row][col] or board[row][col] != color):
            return
        
        visited[row][col] = True
        group_stones.append((row, col))
        
        # 搜索四个方向
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        for dr, dc in directions:
            self._dfs_group(board, visited, row + dr, col + dc, color, group_stones)
    
    def _calculate_liberties(self, board: List[List[int]], 
                           group_stones: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """计算棋块的气（空位）"""
        liberties = set()
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        for row, col in group_stones:
            for dr, dc in directions:
                new_row, new_col = row + dr, col + dc
                if (0 <= new_row < 19 and 0 <= new_col < 19 and 
                    board[new_row][new_col] == 0):
                    liberties.add((new_row, new_col))
        
        return list(liberties)
    
    def predict_territory_for_groups(self, board: List[List[int]], 
                                   stone_groups: List[Dict], 
                                   ownership_data: List[List[float]] = None) -> Dict:
        """为每个棋块预测其控制的领地
        
        Args:
            board: 棋盘状态
            stone_groups: 棋块信息
            ownership_data: KataGo的领地所有权数据（可选）
            
        Returns:
            每个棋块的预测领地信息
        """
        territory_prediction = {}
        
        for group in stone_groups:
            group_id = group["group_id"]
            color = group["color"]
            stones = group["stones"]
            
            if ownership_data:
                # 使用KataGo的ownership数据进行精确预测
                predicted_territory = self._predict_territory_with_ownership(
                    stones, color, ownership_data
                )
            else:
                # 使用简单的距离算法进行基础预测
                predicted_territory = self._predict_territory_simple(
                    board, stones, color
                )
            
            territory_prediction[group_id] = {
                "group_id": group_id,
                "color": color,
                "predicted_territory": predicted_territory,
                "territory_count": len(predicted_territory)
            }
        
        return territory_prediction
    
    def _predict_territory_with_ownership(self, stones: List[Tuple[int, int]], 
                                        color: str, 
                                        ownership_data: List[List[float]]) -> List[Tuple[int, int]]:
        """基于KataGo的ownership数据预测领地"""
        territory = []
        color_threshold = 0.3  # 领地归属的阈值
        
        for row in range(19):
            for col in range(19):
                ownership_value = ownership_data[row][col]
                
                # 根据颜色和ownership值判断领地归属
                if color == "black" and ownership_value > color_threshold:
                    territory.append((row, col))
                elif color == "white" and ownership_value < -color_threshold:
                    territory.append((row, col))
        
        return territory
    
    def _predict_territory_simple(self, board: List[List[int]], 
                                stones: List[Tuple[int, int]], 
                                color: str) -> List[Tuple[int, int]]:
        """简单的领地预测算法（基于距离）"""
        territory = []
        color_value = 1 if color == "black" else 2
        
        # 寻找与该棋块相邻的空位
        visited = set()
        queue = list(stones)
        
        while queue:
            row, col = queue.pop(0)
            
            # 检查四个方向的相邻位置
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            for dr, dc in directions:
                new_row, new_col = row + dr, col + dc
                
                if (0 <= new_row < 19 and 0 <= new_col < 19 and 
                    (new_row, new_col) not in visited):
                    
                    visited.add((new_row, new_col))
                    
                    if board[new_row][new_col] == 0:  # 空位
                        # 简单判断：如果周围主要是同色棋子，则认为是该色领地
                        if self._is_likely_territory(board, new_row, new_col, color_value):
                            territory.append((new_row, new_col))
                            queue.append((new_row, new_col))  # 继续扩展
        
        return territory
    
    def _is_likely_territory(self, board: List[List[int]], row: int, col: int, color: int) -> bool:
        """简单判断某个空位是否可能属于指定颜色的领地"""
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        same_color_count = 0
        opponent_color_count = 0
        opponent_color = 3 - color
        
        for dr, dc in directions:
            new_row, new_col = row + dr, col + dc
            if 0 <= new_row < 19 and 0 <= new_col < 19:
                if board[new_row][new_col] == color:
                    same_color_count += 1
                elif board[new_row][new_col] == opponent_color:
                    opponent_color_count += 1
        
        # 如果同色棋子多于对方棋子，认为可能是该色领地
        return same_color_count > opponent_color_count
    
    def get_placed_stones(self, board: List[List[int]]) -> List[Dict]:
        """获取当前盘面上所有已落子的位置"""
        placed_stones = []
        
        for row in range(19):
            for col in range(19):
                if board[row][col] != 0:
                    stone_info = {
                        "position": (row, col),
                        "color": "black" if board[row][col] == 1 else "white",
                        "move_number": None  # 需要从历史记录中获取
                    }
                    placed_stones.append(stone_info)
        
        return placed_stones
    
    def add_move_data(self, move_number: int, move: str, color: str, 
                     board: List[List[int]], winrate_data: Dict, 
                     recommended_moves: List[Dict] = None,
                     ownership_data: List[List[float]] = None):
        """添加一步棋的完整数据
        
        Args:
            move_number: 手数
            move: 着法（如"D4"或"pass"）
            color: 落子颜色（"black"或"white"）
            board: 当前棋盘状态
            winrate_data: 胜率数据
            recommended_moves: 推荐着法列表
            ownership_data: 领地所有权数据
        """
        # 分析棋块
        stone_groups = self.analyze_stone_groups(board)
        
        # 预测领地
        territory_prediction = self.predict_territory_for_groups(
            board, stone_groups, ownership_data
        )
        
        # 获取已落子信息
        placed_stones = self.get_placed_stones(board)
        
        # 构建完整的步骤数据
        move_data = {
            "move_number": move_number,
            "move": move,
            "color": color,
            "timestamp": datetime.now().isoformat(),
            "winrate_data": winrate_data,
            "stone_groups": stone_groups,
            "territory_prediction": territory_prediction,
            "placed_stones": placed_stones,
            "recommended_moves": recommended_moves or []
        }
        
        self.evolution_data.append(move_data)
        
        # 自动保存到文件
        self.save_to_file()
    
    def save_to_file(self):
        """保存数据到JSON文件"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "game_id": self.game_id,
                    "created_at": datetime.now().isoformat(),
                    "total_moves": len(self.evolution_data) - 1,  # 减去初始状态
                    "evolution_data": self.evolution_data
                }, f, ensure_ascii=False, indent=2)
            print(f"局势演化数据已保存到: {self.storage_path}")
        except Exception as e:
            print(f"保存局势演化数据失败: {e}")
    
    def load_from_file(self, file_path: str) -> bool:
        """从文件加载数据"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.game_id = data.get("game_id", self.game_id)
                    self.evolution_data = data.get("evolution_data", [])
                    self.storage_path = file_path
                    print(f"成功加载局势演化数据: {file_path}")
                    return True
            return False
        except Exception as e:
            print(f"加载局势演化数据失败: {e}")
            return False
    
    def get_move_data(self, move_number: int) -> Optional[Dict]:
        """获取指定手数的数据"""
        for data in self.evolution_data:
            if data["move_number"] == move_number:
                return data
        return None
    
    def get_latest_data(self) -> Optional[Dict]:
        """获取最新的数据"""
        if self.evolution_data:
            return self.evolution_data[-1]
        return None
    
    def get_statistics(self) -> Dict:
        """获取游戏统计信息"""
        if not self.evolution_data:
            return {}
        
        total_moves = len(self.evolution_data) - 1  # 减去初始状态
        latest_data = self.get_latest_data()
        
        stats = {
            "game_id": self.game_id,
            "total_moves": total_moves,
            "current_winrate": latest_data.get("winrate_data", {}),
            "total_stone_groups": len(latest_data.get("stone_groups", [])),
            "total_placed_stones": len(latest_data.get("placed_stones", [])),
            "storage_path": self.storage_path
        }
        
        return stats