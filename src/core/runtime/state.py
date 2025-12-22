# """
# Redis状态管理器
# 管理智能体的运行时状态和生命周期 - 使用系统级配置
# """
#
# import json
# from datetime import datetime
# from typing import Dict, Any, Optional, List
#
# import redis.asyncio as redis
#
# from src.agents.enum.agent_state import AgentState
#
#
# class AgentStateManager:
#     """Agent状态管理器 - 使用系统级配置"""
#
#     def __init__(self, config: Dict[str, Any]):
#         self.config = config
#         self.client: Optional[redis.Redis] = None
#         self._connected = False
#
#     async def connect(self) -> None:
#         """连接到Redis"""
#         if self._connected and self.client:
#             return
#
#         try:
#             connection_params = {
#                 'host': self.config.get('host', 'localhost'),
#                 'port': self.config.get('port', 6379),
#                 'db': self.config.get('db', 0),
#                 'ssl': self.config.get('ssl', False),
#                 'socket_timeout': self.config.get('socket_timeout', 5),
#                 'socket_connect_timeout': self.config.get('socket_connect_timeout', 5),
#                 'retry_on_timeout': self.config.get('retry_on_timeout', True),
#                 'health_check_interval': self.config.get('health_check_interval', 30),
#                 'max_connections': self.config.get('max_connections', 50)
#             }
#
#             if self.config.get('password'):
#                 connection_params['password'] = self.config['password']
#
#             self.client = redis.Redis(**connection_params)
#             await self.client.ping()
#             self._connected = True
#             print(f"✅ Redis连接成功: {self.config.get('host')}:{self.config.get('port')}")
#         except Exception as e:
#             raise ConnectionError(f"Redis连接失败: {e}")
#
#     async def disconnect(self) -> None:
#         """断开Redis连接"""
#         if self.client:
#             await self.client.close()
#             self.client = None
#             self._connected = False
#
#     async def set_agent_state(self, agent_id: int, state: AgentState, metadata: Dict[str, Any] = None) -> bool:
#         """设置智能体状态"""
#         await self.connect()
#
#         state_data = {
#             'state': state.value,
#             'timestamp': datetime.now().isoformat(),
#             'metadata': metadata or {}
#         }
#
#         key = f"agent:{agent_id}:state"
#         ttl = self.config.get('state_ttl', 3600)
#
#         try:
#             await self.client.setex(
#                 key,
#                 ttl,
#                 json.dumps(state_data)
#             )
#             return True
#         except Exception as e:
#             print(f"设置智能体状态失败: {e}")
#             return False
#
#     async def get_agent_state(self, agent_id: int) -> Optional[Dict[str, Any]]:
#         """获取智能体状态"""
#         await self.connect()
#
#         key = f"agent:{agent_id}:state"
#         ttl = self.config.get('state_ttl', 3600)
#
#         try:
#             data = await self.client.get(key)
#             if data:
#                 state_data = json.loads(data)
#                 # 更新TTL
#                 await self.client.expire(key, ttl)
#                 return state_data
#         except Exception as e:e
#             print(f"获取智能体状态失败: {e}")
#
#         return None
#
#     async def update_agent_heartbeat(self, agent_id: int) -> bool:
#         """更新智能体心跳"""
#         await self.connect()
#
#         key = f"agent:{agent_id}:heartbeat"
#         heartbeat_interval = self.config.get('heartbeat_interval', 60)
#
#         try:
#             await self.client.setex(
#                 key,
#                 heartbeat_interval * 2,  # 两倍间隔作为超时时间
#                 datetime.now().isoformat()
#             )
#             return True
#         except Exception as e:
#             print(f"更新智能体心跳失败: {e}")
#             return False
#
#     async def get_agent_heartbeat(self, agent_id: int) -> Optional[str]:
#         """获取智能体最后心跳时间"""
#         await self.connect()
#
#         key = f"agent:{agent_id}:heartbeat"
#         try:
#             return await self.client.get(key)
#         except Exception as e:
#             print(f"获取智能体心跳失败: {e}")
#             return None
#
#     async def is_agent_alive(self, agent_id: int) -> bool:
#         """检查智能体是否存活"""
#         heartbeat = await self.get_agent_heartbeat(agent_id)
#         if not heartbeat:
#             return False
#
#         try:
#             last_heartbeat = datetime.fromisoformat(heartbeat.decode())
#             heartbeat_interval = self.config.get('heartbeat_interval', 60)
#             return (datetime.now() - last_heartbeat).total_seconds() < heartbeat_interval * 1.5
#         except Exception:
#             return False
#
#     async def get_all_active_agents(self) -> List[int]:
#         """获取所有活跃的智能体ID"""
#         await self.connect()
#
#         try:
#             keys = await self.client.keys("agent:*:heartbeat")
#             agent_ids = []
#
#             for key in keys:
#                 # 从key中提取agent_id
#                 parts = key.decode().split(':')
#                 if len(parts) == 3 and parts[0] == "agent" and parts[2] == "heartbeat":
#                     try:
#                         agent_id = int(parts[1])
#                         if await self.is_agent_alive(agent_id):
#                             agent_ids.append(agent_id)
#                     except ValueError:
#                         continue
#
#             return agent_ids
#         except Exception as e:
#             print(f"获取活跃智能体列表失败: {e}")
#             return []
#
#     async def remove_agent_state(self, agent_id: int) -> bool:
#         """移除智能体的所有状态数据"""
#         await self.connect()
#
#         try:
#             # 删除状态键
#             state_key = f"agent:{agent_id}:state"
#             heartbeat_key = f"agent:{agent_id}:heartbeat"
#
#             await self.client.delete(state_key, heartbeat_key)
#             return True
#         except Exception as e:
#             print(f"移除智能体状态失败: {e}")
#             return False
#
#     async def cleanup_expired_states(self) -> int:
#         """清理过期的状态数据"""
#         await self.connect()
#
#         try:
#             # 删除过期的心跳键（由Redis自动处理）
#             # 这里可以添加其他清理逻辑
#             return 0
#         except Exception as e:
#             print(f"清理过期状态失败: {e}")
#             return 0
