import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import copy
from pymongo.errors import PyMongoError, DuplicateKeyError
from .mongodb_config import mongo_config
from .mongodb_schema import MongoDBSchema, COLLECTION_NAMES

class GameEvolutionMongoDB:
    """对局局势演化MongoDB存储系统
    
    负责存储和管理每步棋的详细数据到MongoDB，包括：
    - 胜率和目差
    - 棋块编号和分析
    - 领地预测坐标
    - 已落子数组
    - 推荐落点数据
    """
    
    def __init__(self, game_id: str = None):
        self.game_id = game_id or self._generate_game_id()
        self.collection_name = COLLECTION_NAMES["GAME_EVOLUTION"]
        self.collection = None
        self._initialize_collection()
        
        # 创建或获取游戏文档
        self._initialize_game_document()
    
    def _generate_game_id(self) -> str:
        """生成唯一的游戏ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"game_{timestamp}"
    
    def _initialize_collection(self):
        """初始化MongoDB集合连接"""
        try:
            self.collection = mongo_config.get_collection(self.collection_name)
            print(f"✅ 成功连接到集合: {self.collection_name}")
        except Exception as e:
            print(f"❌ 连接集合失败: {e}")
            raise
    
    def _initialize_game_document(self):
        """初始化游戏文档"""
        try:
            # 检查游戏文档是否已存在
            existing_doc = self.collection.find_one({"game_id": self.game_id})
            
            if not existing_doc:
                # 创建新的游戏文档
                initial_doc = MongoDBSchema.create_sample_document(self.game_id)
                result = self.collection.insert_one(initial_doc)
                print(f"✅ 创建新游戏文档: {self.game_id}, MongoDB ID: {result.inserted_id}")
            else:
                print(f"📄 找到现有游戏文档: {self.game_id}")
                
        except Exception as e:
            print(f"❌ 初始化游戏文档失败: {e}")
            raise
    
    def analyze_stone_groups(self, board: List[List[int]]) -> List[Dict]:
        """分析棋盘上的棋块
        
        Args:
            board: 19x19的棋盘状态，0=空，1=黑，2=白
            
        Returns:
            List[Dict]: 棋块信息列表
        """
        if not board or len(board) != 19 or len(board[0]) != 19:
            return []
        
        visited = [[False] * 19 for _ in range(19)]
        groups = []
        group_id = 0
        
        def get_neighbors(x, y):
            neighbors = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < 19 and 0 <= ny < 19:
                    neighbors.append((nx, ny))
            return neighbors
        
        def dfs(x, y, color, group_stones):
            if visited[x][y] or board[x][y] != color:
                return
            
            visited[x][y] = True
            group_stones.append([x, y])
            
            for nx, ny in get_neighbors(x, y):
                if not visited[nx][ny] and board[nx][ny] == color:
                    dfs(nx, ny, color, group_stones)
        
        def count_liberties(group_stones, color):
            liberties = set()
            for x, y in group_stones:
                for nx, ny in get_neighbors(x, y):
                    if board[nx][ny] == 0:  # 空点
                        liberties.add((nx, ny))
            return len(liberties)
        
        # 遍历棋盘找到所有棋块
        for i in range(19):
            for j in range(19):
                if board[i][j] != 0 and not visited[i][j]:
                    group_stones = []
                    color = board[i][j]
                    dfs(i, j, color, group_stones)
                    
                    if group_stones:
                        liberties = count_liberties(group_stones, color)
                        groups.append({
                            "group_id": group_id,
                            "color": "black" if color == 1 else "white",
                            "stones": group_stones,
                            "liberties": liberties,
                            "is_alive": liberties > 0
                        })
                        group_id += 1
        
        return groups
    
    def add_move_data(self, move_number: int, move: str, color: str, 
                     winrate_data: Dict, board: List[List[int]] = None,
                     territory_data: Dict = None, recommended_moves: List = None):
        """添加一步棋的数据到MongoDB
        
        Args:
            move_number: 步数
            move: 着法，如"D4"
            color: 棋子颜色
            winrate_data: 胜率数据
            board: 棋盘状态
            territory_data: 领地数据
            recommended_moves: 推荐着法
        """
        try:
            print(f"🔄 添加第{move_number}步数据到MongoDB: {move}")
            
            # 分析棋块
            stone_groups = self.analyze_stone_groups(board) if board else []
            
            # 获取已落子位置
            placed_stones = []
            if board:
                for i in range(19):
                    for j in range(19):
                        if board[i][j] != 0:
                            placed_stones.append({
                                "position": [i, j],
                                "color": "black" if board[i][j] == 1 else "white"
                            })
            
            # 处理领地数据
            territory_prediction = {
                "black_territory": [],
                "white_territory": [],
                "neutral_points": []
            }
            
            if territory_data:
                if isinstance(territory_data, list) and len(territory_data) == 19:
                    # 处理二维数组格式的ownership数据
                    for row in range(19):
                        for col in range(19):
                            if row < len(territory_data) and col < len(territory_data[row]):
                                ownership_value = territory_data[row][col]
                                if ownership_value > 0.6:  # 黑棋领地
                                    territory_prediction["black_territory"].append([row, col])
                                elif ownership_value < -0.6:  # 白棋领地
                                    territory_prediction["white_territory"].append([row, col])
                                else:  # 中性点
                                    territory_prediction["neutral_points"].append([row, col])
                elif isinstance(territory_data, dict):
                    # 处理字典格式的领地数据
                    territory_prediction = territory_data
            
            # 构建移动数据
            move_data = {
                "move_number": move_number,
                "move": move,
                "color": color,
                "timestamp": datetime.now(),
                "winrate_data": winrate_data or {
                    "black_winrate": 50.0,
                    "white_winrate": 50.0,
                    "score_lead": 0.0
                },
                "stone_groups": stone_groups,
                "territory_prediction": territory_prediction,
                "placed_stones": placed_stones,
                "recommended_moves": recommended_moves or []
            }
            
            # 更新MongoDB文档
            result = self.collection.update_one(
                {"game_id": self.game_id},
                {
                    "$push": {"evolution_data": move_data},
                    "$set": {
                        "updated_at": datetime.now(),
                        "total_moves": move_number
                    }
                }
            )
            
            if result.modified_count > 0:
                print(f"✅ 成功添加第{move_number}步数据到MongoDB")
            else:
                print(f"⚠️ 未能更新MongoDB文档，可能文档不存在")
                
        except Exception as e:
            print(f"❌ 添加移动数据到MongoDB失败: {e}")
            import traceback
            traceback.print_exc()
    
    def get_game_data(self) -> Optional[Dict]:
        """获取完整的游戏数据
        
        Returns:
            Dict: 游戏数据，如果不存在返回None
        """
        try:
            doc = self.collection.find_one({"game_id": self.game_id})
            if doc:
                # 转换ObjectId为字符串
                doc["_id"] = str(doc["_id"])
                return doc
            return None
        except Exception as e:
            print(f"❌ 获取游戏数据失败: {e}")
            return None
    
    def get_evolution_data(self) -> List[Dict]:
        """获取局势演化数据
        
        Returns:
            List[Dict]: 演化数据列表
        """
        try:
            doc = self.collection.find_one(
                {"game_id": self.game_id},
                {"evolution_data": 1}
            )
            return doc.get("evolution_data", []) if doc else []
        except Exception as e:
            print(f"❌ 获取演化数据失败: {e}")
            return []
    
    def update_game_status(self, status: str, final_result: Dict = None):
        """更新游戏状态
        
        Args:
            status: 游戏状态 (active, finished, abandoned)
            final_result: 最终结果数据
        """
        try:
            update_data = {
                "game_status": status,
                "updated_at": datetime.now()
            }
            
            if final_result:
                update_data["final_result"] = final_result
            
            result = self.collection.update_one(
                {"game_id": self.game_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                print(f"✅ 成功更新游戏状态: {status}")
            else:
                print(f"⚠️ 未能更新游戏状态")
                
        except Exception as e:
            print(f"❌ 更新游戏状态失败: {e}")
    
    def delete_game(self) -> bool:
        """删除游戏数据
        
        Returns:
            bool: 是否删除成功
        """
        try:
            result = self.collection.delete_one({"game_id": self.game_id})
            if result.deleted_count > 0:
                print(f"✅ 成功删除游戏数据: {self.game_id}")
                return True
            else:
                print(f"⚠️ 未找到要删除的游戏数据: {self.game_id}")
                return False
        except Exception as e:
            print(f"❌ 删除游戏数据失败: {e}")
            return False
    
    def get_game_statistics(self) -> Dict:
        """获取游戏统计信息
        
        Returns:
            Dict: 统计信息
        """
        try:
            doc = self.get_game_data()
            if not doc:
                return {}
            
            evolution_data = doc.get("evolution_data", [])
            
            return {
                "game_id": self.game_id,
                "total_moves": doc.get("total_moves", 0),
                "game_status": doc.get("game_status", "unknown"),
                "created_at": doc.get("created_at"),
                "updated_at": doc.get("updated_at"),
                "players": doc.get("players", {}),
                "evolution_entries": len(evolution_data)
            }
        except Exception as e:
            print(f"❌ 获取游戏统计失败: {e}")
            return {}
    
    @classmethod
    def list_games(cls, limit: int = 10, status: str = None) -> List[Dict]:
        """列出游戏列表
        
        Args:
            limit: 返回数量限制
            status: 过滤游戏状态
            
        Returns:
            List[Dict]: 游戏列表
        """
        try:
            collection = mongo_config.get_collection(COLLECTION_NAMES["GAME_EVOLUTION"])
            
            query = {}
            if status:
                query["game_status"] = status
            
            cursor = collection.find(
                query,
                {"game_id": 1, "created_at": 1, "updated_at": 1, 
                 "total_moves": 1, "game_status": 1, "players": 1}
            ).sort("created_at", -1).limit(limit)
            
            games = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                games.append(doc)
            
            return games
        except Exception as e:
            print(f"❌ 获取游戏列表失败: {e}")
            return []
    
    def get_statistics(self) -> Dict:
        """获取游戏统计信息（兼容性方法）
        
        Returns:
            Dict: 统计信息
        """
        return self.get_game_statistics()
    
    def get_latest_data(self) -> Optional[Dict]:
        """获取最新的移动数据
        
        Returns:
            Dict: 最新移动数据，如果没有数据返回None
        """
        try:
            evolution_data = self.get_evolution_data()
            if evolution_data:
                return evolution_data[-1]  # 返回最后一个元素
            return None
        except Exception as e:
            print(f"❌ 获取最新数据失败: {e}")
            return None
    
    def get_move_data(self, move_number: int) -> Optional[Dict]:
        """获取指定步数的移动数据
        
        Args:
            move_number: 步数（从0开始）
            
        Returns:
            Dict: 指定步数的数据，如果不存在返回None
        """
        try:
            evolution_data = self.get_evolution_data()
            if 0 <= move_number < len(evolution_data):
                return evolution_data[move_number]
            return None
        except Exception as e:
            print(f"❌ 获取第{move_number}步数据失败: {e}")
            return None
    
    @property
    def evolution_data(self) -> List[Dict]:
        """兼容性属性：获取演化数据列表
        
        Returns:
            List[Dict]: 演化数据列表
        """
        return self.get_evolution_data()

    def save_to_file(self):
        """兼容性方法：保存到MongoDB（不再保存到文件）"""
        print(f"📊 游戏数据已自动保存到MongoDB: {self.game_id}")
        # 获取统计信息用于日志
        stats = self.get_game_statistics()
        print(f"📈 游戏统计: 总步数={stats.get('total_moves', 0)}, 状态={stats.get('game_status', 'unknown')}")