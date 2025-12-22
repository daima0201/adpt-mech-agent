# """
# 统一配置管理器 - 对外提供完整功能
# """
#
# from typing import Dict, Any, Optional, List
# import json
#
# class ConfigManager:
#     """配置管理器 - 所有配置相关业务逻辑在这里"""
#
#     def __init__(self, llm_repo, agent_repo, cache):
#         self.llm_repo = llm_repo
#         self.agent_repo = agent_repo
#         self.cache = cache
#
#     async def get_agent_config(self, agent_id: int) -> Optional[Dict[str, Any]]:
#         """获取智能体配置（带缓存）"""
#         cache_key = f"agent:config:{agent_id}"
#
#         # 1. 检查缓存
#         cached = await self.cache.get(cache_key)
#         if cached:
#             return json.loads(cached)cached
#
#         # 2. 查询数据库
#         config = await self.agent_repo.get_full_agent_config(agent_id)
#         if not config:
#             return None
#
#         # 3. 写入缓存
#         await self.cache.set(cache_key, json.dumps(config), ttl=300)
#
#         return config
#
#     async def get_complete_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
#         """根据名称获取完整的智能体配置"""
#         # 首先通过名称查找agent_id
#         agent = await self.agent_repo.get_by_name(agent_name)
#         if not agent:
#             return None
#
#         # 使用现有的get_agent_config方法获取完整配置
#         return await self.get_agent_config(agent.id)
#
#     async def save_agent_profile(self, profile: Dict[str, Any], agent_config_name: str):
#         """保存智能体配置文件"""
#         # 首先通过名称查找agent_id
#         agent = await self.agent_repo.get_by_name(agent_config_name)
#         if not agent:
#             raise ValueError(f"智能体配置不存在: {agent_config_name}")
#
#         # 更新profile数据
#         await self.agent_repo.update_agent_profile(agent.id, profile)
#
#         # 清除缓存
#         await self.cache.delete(f"agent:config:{agent.id}")
#
#     async def get_agent_profile(self, agent_config_name: str) -> Optional[Dict[str, Any]]:
#         """获取智能体配置文件"""
#         # 首先通过名称查找agent_id
#         agent = await self.agent_repo.get_by_name(agent_config_name)
#         if not agent:
#             return None
#
#         # 获取完整配置并提取profile部分
#         full_config = await self.get_agent_config(agent.id)
#         if full_config and 'profile' in full_config:
#             return full_config['profile']
#         return None
#
#     async def create_agent_config(
#         self,
#         name: str,
#         agent_type: str,
#         system_prompt: str,
#         llm_config_id: int,
#         profile_data: Dict[str, Any]
#     ) -> Dict[str, Any]:
#         """创建智能体配置"""
#         # 1. 验证数据
#         if not await self._validate_llm_config(llm_config_id):
#             raise ValueError(f"LLM配置不存在: {llm_config_id}")
#
#         # 2. 创建Agent配置
#         agent_data = {
#             "name": name,
#             "agent_type": agent_type,
#             "system_prompt": system_prompt,
#             "llm_config_id": llm_config_id
#         }
#
#         result = await self.agent_repo.create_agent_with_dependencies(
#             agent_data, profile_data
#         )
#
#         # 3. 清除相关缓存
#         await self.cache.delete(f"agent:config:{result['agent'].id}")
#
#         return result
#
#     async def update_agent_config(
#         self,
#         agent_id: int,
#         **updates
#     ) -> Optional[Dict[str, Any]]:
#         """更新智能体配置"""
#         # 1. 验证更新数据
#         if 'llm_config_id' in updates:
#             if not await self._validate_llm_config(updates['llm_config_id']):
#                 raise ValueError(f"LLM配置不存在: {updates['llm_config_id']}")
#
#         # 2. 更新配置
#         updated = await self.agent_repo.update_agent(agent_id, **updates)
#         if not updated:
#             return None
#
#         # 3. 清除缓存
#         await self.cache.delete(f"agent:config:{agent_id}")
#
#         # 4. 返回更新后的完整配置
#         return await self.get_agent_config(agent_id)
#
#     async def list_active_agents(self) -> List[Dict[str, Any]]:
#         """获取所有活跃的智能体"""
#         agents = await self.agent_repo.list_active_agents()
#
#         results = []
#         for agent in agents:
#             config = await self.get_agent_config(agent.id)
#             if config:
#                 results.append(config)
#
#         return results
#
#     async def get_llm_config(self, llm_id: int) -> Optional[Dict[str, Any]]:
#         """获取LLM配置"""
#         cache_key = f"llm:config:{llm_id}"
#
#         # 1. 检查缓存
#         cached = await self.cache.get(cache_key)
#         if cached:
#             return json.loads(cached)
#
#         # 2. 查询数据库
#         llm_config = await self.llm_repo.get(llm_id)
#         if not llm_config:
#             return None
#
#         # 3. 写入缓存
#         await self.cache.set(cache_key, json.dumps(llm_config.to_dict()), ttl=600)
#
#         return llm_config.to_dict()
#
#     async def list_active_llms(self) -> List[Dict[str, Any]]:
#         """获取所有活跃的LLM配置"""
#         llms = await self.llm_repo.list_active_llms()
#         return [llm.to_dict() for llm in llms]
#
#     async def _validate_llm_config(self, llm_id: int) -> bool:
#         """验证LLM配置是否存在"""
#         llm_config = await self.llm_repo.get(llm_id)
#         return llm_config is not None and llm_config.is_active