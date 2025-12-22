"""
工具注册和管理系统
提供工具发现、注册和查找功能
"""

from typing import Dict, List, Optional, Any
from src.capabilities.tools.base import Tool, AsyncTool

class ToolRegistry:
    """工具注册表 - 单例模式"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._tools: Dict[str, Tool] = {}
            self._categories: Dict[str, List[str]] = {}
            self._tags: Dict[str, List[str]] = {}
            self._metadata: Dict[str, Dict[str, Any]] = {}
            self._usage_stats: Dict[str, Dict[str, int]] = {}
            self._initialized = True
    
    def register_tool(self, tool: Tool, category: str = "general",
                     tags: Optional[List[str]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """注册工具"""
        
        if tool.name in self._tools:
            raise ValueError(f"工具 '{tool.name}' 已经注册")
        
        self._tools[tool.name] = tool
        
        # 添加到分类
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool.name)
        
        # 添加标签
        if tags:
            for tag in tags:
                if tag not in self._tags:
                    self._tags[tag] = []
                self._tags[tag].append(tool.name)
        
        # 存储元数据
        self._metadata[tool.name] = metadata or {}
        self._metadata[tool.name]['category'] = category
        self._metadata[tool.name]['tags'] = tags or []
        self._metadata[tool.name]['registration_time'] = self._get_timestamp()
        
        # 初始化使用统计
        self._usage_stats[tool.name] = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'last_called': None
        }
    
    def unregister_tool(self, tool_name: str) -> bool:
        """注销工具"""
        
        if tool_name not in self._tools:
            return False
        
        # 从分类中移除
        category = self._metadata[tool_name].get('category', 'general')
        if category in self._categories and tool_name in self._categories[category]:
            self._categories[category].remove(tool_name)
        
        # 从标签中移除
        tags = self._metadata[tool_name].get('tags', [])
        for tag in tags:
            if tag in self._tags and tool_name in self._tags[tag]:
                self._tags[tag].remove(tool_name)
        
        # 移除工具和元数据
        del self._tools[tool_name]
        del self._metadata[tool_name]
        if tool_name in self._usage_stats:
            del self._usage_stats[tool_name]
        
        return True
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """获取工具"""
        return self._tools.get(tool_name)
    
    def list_tools(self, category: Optional[str] = None,
                  tags: Optional[List[str]] = None) -> List[str]:
        """列出工具名称"""
        
        if category and tags:
            # 按分类和标签过滤
            category_tools = set(self._categories.get(category, []))
            tagged_tools = set()
            
            for tag in tags:
                if tag in self._tags:
                    tagged_tools.update(self._tags[tag])
            
            return list(category_tools.intersection(tagged_tools))
        
        elif category:
            # 按分类过滤
            return self._categories.get(category, []).copy()
        
        elif tags:
            # 按标签过滤
            result = set()
            for tag in tags:
                if tag in self._tags:
                    result.update(self._tags[tag])
            return list(result)
        
        else:
            # 返回所有工具
            return list(self._tools.keys())
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """按分类获取工具"""
        
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names]
    
    def search_tools(self, query: str, search_fields: List[str] = None) -> List[str]:
        """搜索工具"""
        
        if search_fields is None:
            search_fields = ['name', 'description']
        
        query_lower = query.lower()
        results = []
        
        for tool_name, tool in self._tools.items():
            for field in search_fields:
                if field == 'name' and query_lower in tool_name.lower():
                    results.append(tool_name)
                    break
                elif field == 'description' and hasattr(tool, 'description') and query_lower in tool.description.lower():
                    results.append(tool_name)
                    break
        
        return results
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具详细信息"""
        
        if tool_name not in self._tools:
            return None
        
        tool = self._tools[tool_name]
        
        info = {
            'name': tool.name,
            'description': tool.description,
            'schema': tool.get_schema(),
            'is_async': isinstance(tool, AsyncTool),
            'categories': [],
            'tags': [],
            'usage_stats': self._usage_stats.get(tool_name, {})
        }
        
        # 查找分类
        for category, tools in self._categories.items():
            if tool_name in tools:
                info['categories'].append(category)
        
        # 查找标签
        for tag, tools in self._tags.items():
            if tool_name in tools:
                info['tags'].append(tag)
        
        return info
    
    def record_tool_usage(self, tool_name: str, success: bool) -> None:
        """记录工具使用情况"""
        
        if tool_name not in self._usage_stats:
            return
        
        import time
        
        stats = self._usage_stats[tool_name]
        stats['total_calls'] += 1
        
        if success:
            stats['successful_calls'] += 1
        else:
            stats['failed_calls'] += 1
        
        stats['last_called'] = time.time()
        stats['success_rate'] = stats['successful_calls'] / stats['total_calls'] if stats['total_calls'] > 0 else 0
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """获取使用统计"""
        
        total_stats = {
            'total_tools': len(self._tools),
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'categories': {},
            'most_used_tools': [],
            'least_used_tools': []
        }
        
        # 汇总统计
        for tool_name, stats in self._usage_stats.items():
            total_stats['total_calls'] += stats['total_calls']
            total_stats['successful_calls'] += stats['successful_calls']
            total_stats['failed_calls'] += stats['failed_calls']
        
        # 按分类统计
        for category, tools in self._categories.items():
            category_stats = {
                'tools_count': len(tools),
                'total_calls': 0,
                'success_rate': 0
            }
            
            for tool_name in tools:
                if tool_name in self._usage_stats:
                    stats = self._usage_stats[tool_name]
                    category_stats['total_calls'] += stats['total_calls']
            
            total_stats['categories'][category] = category_stats
        
        # 最常用和最不常用工具
        if self._usage_stats:
            sorted_by_usage = sorted(
                self._usage_stats.items(),
                key=lambda x: x[1]['total_calls'],
                reverse=True
            )
            
            total_stats['most_used_tools'] = [
                {'tool': name, 'calls': stats['total_calls']}
                for name, stats in sorted_by_usage[:5]
            ]
            
            total_stats['least_used_tools'] = [
                {'tool': name, 'calls': stats['total_calls']}
                for name, stats in sorted_by_usage[-5:]
            ]
        
        return total_stats
    
    def validate_tool_dependencies(self, tool_name: str) -> Dict[str, Any]:
        """验证工具依赖关系"""
        
        if tool_name not in self._tools:
            return {'valid': False, 'error': f"工具 '{tool_name}' 未注册"}
        
        tool = self._tools[tool_name]
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': []
        }
        
        # 检查工具模式
        try:
            schema = tool.get_schema()
            
            # 验证参数定义
            if 'parameters' not in schema:
                validation_result['warnings'].append("工具没有定义参数")
            
            # 检查必需参数
            required_params = schema.get('parameters', {}).get('required', [])
            for param in required_params:
                param_info = schema['parameters']['properties'].get(param, {})
                if 'description' not in param_info:
                    validation_result['warnings'].append(f"必需参数 '{param}' 缺少描述")
        
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"模式获取失败: {str(e)}")
        
        return validation_result
    
    def export_registry(self) -> Dict[str, Any]:
        """导出注册表状态"""
        
        export_data = {
            'tools': {},
            'categories': self._categories.copy(),
            'tags': self._tags.copy(),
            'usage_stats': self._usage_stats.copy(),
            'metadata': {
                'export_time': self._get_timestamp(),
                'total_tools': len(self._tools)
            }
        }
        
        # 导出工具信息（不包含工具实例）
        for tool_name, tool in self._tools.items():
            export_data['tools'][tool_name] = {
                'description': tool.description,
                'schema': tool.get_schema(),
                'is_async': isinstance(tool, AsyncTool)
            }
        
        return export_data
    
    def import_registry(self, data: Dict[str, Any]) -> bool:
        """导入注册表状态"""
        
        try:
            # 清空当前注册表
            self._tools.clear()
            self._categories.clear()
            self._tags.clear()
            self._usage_stats.clear()
            
            # 导入数据
            if 'categories' in data:
                self._categories = data['categories'].copy()
            
            if 'tags' in data:
                self._tags = data['tags'].copy()
            
            if 'usage_stats' in data:
                self._usage_stats = data['usage_stats'].copy()
            
            return True
            
        except Exception as e:
            print(f"导入注册表失败: {str(e)}")
            return False
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
class GlobalToolRegistry:
    """全局工具注册表（单例模式）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._registry = ToolRegistry()
        return cls._instance
    
    def register_tool(self, tool: Tool, category: str = "general",
                     tags: Optional[List[str]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """注册工具到全局注册表"""
        self._registry.register_tool(tool, category, tags, metadata)
    
    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """从全局注册表获取工具"""
        return self._registry.get_tool(tool_name)
    
    def list_tools(self, category: Optional[str] = None,
                  tags: Optional[List[str]] = None) -> List[str]:
        """列出全局注册表中的工具"""
        return self._registry.list_tools(category, tags)
    
    def get_tools_by_category(self, category: str) -> List[Tool]:
        """按分类获取工具"""
        return self._registry.get_tools_by_category(category)
    
    def search_tools(self, query: str, search_fields: List[str] = None) -> List[str]:
        """搜索工具"""
        return self._registry.search_tools(query, search_fields)
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具详细信息"""
        return self._registry.get_tool_info(tool_name)
    
    def record_tool_usage(self, tool_name: str, success: bool) -> None:
        """记录工具使用情况"""
        self._registry.record_tool_usage(tool_name, success)
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """获取使用统计"""
        return self._registry.get_usage_statistics()
    
    def validate_tool_dependencies(self, tool_name: str) -> Dict[str, Any]:
        """验证工具依赖关系"""
        return self._registry.validate_tool_dependencies(tool_name)
    
    def export_registry(self) -> Dict[str, Any]:
        """导出注册表状态"""
        return self._registry.export_registry()
    
    def import_registry(self, data: Dict[str, Any]) -> bool:
        """导入注册表状态"""
        return self._registry.import_registry(data)


# 便捷函数
def register_tool(tool: Tool, category: str = "general",
                 tags: Optional[List[str]] = None,
                 metadata: Optional[Dict[str, Any]] = None) -> None:
    """便捷函数：注册工具到全局注册表"""
    GlobalToolRegistry().register_tool(tool, category, tags, metadata)


def get_tool(tool_name: str) -> Optional[Tool]:
    """便捷函数：从全局注册表获取工具"""
    return GlobalToolRegistry().get_tool(tool_name)


def list_tools(category: Optional[str] = None,
               tags: Optional[List[str]] = None) -> List[str]:
    """便捷函数：列出全局注册表中的工具"""
    return GlobalToolRegistry().list_tools(category, tags)


def search_tools(query: str, search_fields: List[str] = None) -> List[str]:
    """便捷函数：搜索工具"""
    return GlobalToolRegistry().search_tools(query, search_fields)


def get_tool_info(tool_name: str) -> Optional[Dict[str, Any]]:
    """便捷函数：获取工具详细信息"""
    return GlobalToolRegistry().get_tool_info(tool_name)


def record_tool_usage(tool_name: str, success: bool) -> None:
    """便捷函数：记录工具使用情况"""
    GlobalToolRegistry().record_tool_usage(tool_name, success)


def get_usage_statistics() -> Dict[str, Any]:
    """便捷函数：获取使用统计"""
    return GlobalToolRegistry().get_usage_statistics()