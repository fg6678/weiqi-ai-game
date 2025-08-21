import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Optional

class MongoDBConfig:
    """
    MongoDB连接配置和管理类
    """
    
    def __init__(self):
        # MongoDB连接配置
        self.host = os.getenv('MONGODB_HOST', 'localhost')
        self.port = int(os.getenv('MONGODB_PORT', 27017))
        self.database_name = os.getenv('MONGODB_DATABASE', 'weiqi_game')
        self.username = os.getenv('MONGODB_USERNAME', None)
        self.password = os.getenv('MONGODB_PASSWORD', None)
        
        # 连接字符串
        if self.username and self.password:
            self.connection_string = f"mongodb://{self.username}:{self.password}@{self.host}:{self.port}/{self.database_name}"
        else:
            self.connection_string = f"mongodb://{self.host}:{self.port}"
        
        self.client: Optional[MongoClient] = None
        self.database = None
    
    def connect(self) -> bool:
        """
        连接到MongoDB数据库
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000,  # 5秒超时
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            
            # 测试连接
            self.client.admin.command('ping')
            self.database = self.client[self.database_name]
            
            print(f"✅ 成功连接到MongoDB: {self.host}:{self.port}/{self.database_name}")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"❌ MongoDB连接失败: {e}")
            print(f"连接字符串: {self.connection_string}")
            return False
        except Exception as e:
            print(f"❌ MongoDB连接出现未知错误: {e}")
            return False
    
    def disconnect(self):
        """
        断开MongoDB连接
        """
        if self.client:
            self.client.close()
            self.client = None
            self.database = None
            print("🔌 MongoDB连接已断开")
    
    def get_database(self):
        """
        获取数据库实例
        
        Returns:
            Database: MongoDB数据库实例
        """
        if self.database is None:
            if not self.connect():
                raise ConnectionError("无法连接到MongoDB数据库")
        return self.database
    
    def get_collection(self, collection_name: str):
        """
        获取集合实例
        
        Args:
            collection_name (str): 集合名称
            
        Returns:
            Collection: MongoDB集合实例
        """
        database = self.get_database()
        return database[collection_name]
    
    def is_connected(self) -> bool:
        """
        检查是否已连接到MongoDB
        
        Returns:
            bool: 是否已连接
        """
        if self.client is None:
            return False
        
        try:
            self.client.admin.command('ping')
            return True
        except Exception:
            return False

# 全局MongoDB配置实例
mongo_config = MongoDBConfig()