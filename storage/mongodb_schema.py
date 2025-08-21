from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class MongoDBSchema:
    """
    MongoDB集合结构和文档模式定义
    """
    
    # 集合名称
    GAME_EVOLUTION_COLLECTION = "game_evolution"
    GAME_METADATA_COLLECTION = "game_metadata"
    
    @staticmethod
    def get_game_evolution_schema() -> Dict[str, Any]:
        """
        游戏局势演化文档结构
        
        Returns:
            Dict: 文档结构示例
        """
        return {
            "_id": "ObjectId",  # MongoDB自动生成的ID
            "game_id": "string",  # 游戏唯一标识符
            "created_at": "datetime",  # 游戏创建时间
            "updated_at": "datetime",  # 最后更新时间
            "total_moves": "int",  # 总步数
            "game_status": "string",  # 游戏状态: active, finished, abandoned
            "players": {
                "black": "string",  # 黑棋玩家
                "white": "string"   # 白棋玩家
            },
            "evolution_data": [  # 局势演化数据数组
                {
                    "move_number": "int",  # 步数
                    "move": "string",  # 着法，如"D4"或"game_start"
                    "color": "string",  # 棋子颜色: "black", "white", null
                    "timestamp": "datetime",  # 时间戳
                    "winrate_data": {
                        "black_winrate": "float",  # 黑棋胜率
                        "white_winrate": "float",  # 白棋胜率
                        "score_lead": "float"      # 目差
                    },
                    "stone_groups": [  # 棋块信息
                        {
                            "group_id": "int",
                            "color": "string",
                            "stones": ["array of coordinates"],
                            "liberties": "int",
                            "is_alive": "bool"
                        }
                    ],
                    "territory_prediction": {  # 领地预测
                        "black_territory": ["array of coordinates"],
                        "white_territory": ["array of coordinates"],
                        "neutral_points": ["array of coordinates"]
                    },
                    "placed_stones": [  # 已落子位置
                        {
                            "position": ["int", "int"],  # [x, y]
                            "color": "string"
                        }
                    ],
                    "recommended_moves": [  # 推荐着法
                        {
                            "position": ["int", "int"],
                            "winrate": "float",
                            "visits": "int",
                            "score_lead": "float"
                        }
                    ]
                }
            ]
        }
    
    @staticmethod
    def get_game_metadata_schema() -> Dict[str, Any]:
        """
        游戏元数据文档结构（可选，用于快速查询）
        
        Returns:
            Dict: 元数据文档结构示例
        """
        return {
            "_id": "ObjectId",
            "game_id": "string",
            "created_at": "datetime",
            "updated_at": "datetime",
            "game_status": "string",
            "total_moves": "int",
            "players": {
                "black": "string",
                "white": "string"
            },
            "final_result": {
                "winner": "string",  # "black", "white", "draw"
                "score": "string",   # 比分描述
                "reason": "string"   # 胜负原因
            },
            "game_settings": {
                "board_size": "int",
                "komi": "float",
                "time_control": "string"
            }
        }
    
    @staticmethod
    def get_indexes() -> List[Dict[str, Any]]:
        """
        推荐的索引配置
        
        Returns:
            List[Dict]: 索引配置列表
        """
        return [
            # 游戏演化集合索引
            {
                "collection": GAME_EVOLUTION_COLLECTION,
                "indexes": [
                    {"game_id": 1},  # 游戏ID索引
                    {"created_at": -1},  # 创建时间倒序索引
                    {"game_status": 1},  # 游戏状态索引
                    {"total_moves": 1},  # 总步数索引
                    {"game_id": 1, "updated_at": -1}  # 复合索引
                ]
            },
            # 游戏元数据集合索引
            {
                "collection": GAME_METADATA_COLLECTION,
                "indexes": [
                    {"game_id": 1},  # 游戏ID唯一索引
                    {"created_at": -1},  # 创建时间倒序索引
                    {"game_status": 1},  # 游戏状态索引
                    {"players.black": 1},  # 黑棋玩家索引
                    {"players.white": 1}   # 白棋玩家索引
                ]
            }
        ]
    
    @staticmethod
    def create_sample_document(game_id: str) -> Dict[str, Any]:
        """
        创建示例文档
        
        Args:
            game_id (str): 游戏ID
            
        Returns:
            Dict: 示例文档
        """
        now = datetime.now()
        return {
            "game_id": game_id,
            "created_at": now,
            "updated_at": now,
            "total_moves": 0,
            "game_status": "active",
            "players": {
                "black": "Human",
                "white": "KataGo"
            },
            "evolution_data": [
                {
                    "move_number": 0,
                    "move": "game_start",
                    "color": None,
                    "timestamp": now,
                    "winrate_data": {
                        "black_winrate": 50.0,
                        "white_winrate": 50.0,
                        "score_lead": 0.0
                    },
                    "stone_groups": [],
                    "territory_prediction": {
                        "black_territory": [],
                        "white_territory": [],
                        "neutral_points": []
                    },
                    "placed_stones": [],
                    "recommended_moves": []
                }
            ]
        }

# 常量定义
COLLECTION_NAMES = {
    "GAME_EVOLUTION": MongoDBSchema.GAME_EVOLUTION_COLLECTION,
    "GAME_METADATA": MongoDBSchema.GAME_METADATA_COLLECTION
}