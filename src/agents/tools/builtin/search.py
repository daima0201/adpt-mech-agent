"""
内置搜索工具
提供本地和网络搜索功能
"""

import os
import re
from typing import Dict, List, Any, Optional
from src.agents.tools import Tool


class SearchTool(Tool):
    """基础搜索工具"""
    
    def __init__(self):
        super().__init__(
            name="search",
            description="执行文本搜索，支持文件内容搜索和模式匹配",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词或表达式"
                    },
                    "search_type": {
                        "type": "string",
                        "description": "搜索类型：text（文本搜索）、regex（正则搜索）",
                        "enum": ["text", "regex"],
                        "default": "text"
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "是否区分大小写",
                        "default": false
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "最大返回结果数",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        )
        self.search_history: List[Dict[str, Any]] = []
    
    def execute(self, query: str, search_type: str = "text",
               case_sensitive: bool = False, max_results: int = 10) -> Dict[str, Any]:
        """执行搜索"""
        
        try:
            if search_type == "text":
                results = self._text_search(query, case_sensitive, max_results)
            elif search_type == "regex":
                results = self._regex_search(query, case_sensitive, max_results)
            else:
                raise ValueError(f"不支持的搜索类型: {search_type}")
            
            # 记录搜索历史
            search_record = {
                'query': query,
                'type': search_type,
                'results_count': len(results),
                'timestamp': self._get_timestamp()
            }
            self.search_history.append(search_record)
            
            # 限制历史记录大小
            if len(self.search_history) > 100:
                self.search_history = self.search_history[-100:]
            
            return {
                "success": True,
                "query": query,
                "search_type": search_type,
                "results": results,
                "total_results": len(results),
                "search_id": len(self.search_history),
                "parameters": {
                    "case_sensitive": case_sensitive,
                    "max_results": max_results
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "search_type": search_type,
                "results": [],
                "total_results": 0
            }
    
    def _text_search(self, query: str, case_sensitive: bool, max_results: int) -> List[Dict[str, Any]]:
        """文本搜索"""
        
        # 在当前工作目录中搜索
        results = []
        search_dir = os.getcwd()
        
        # 准备查询
        search_pattern = query if case_sensitive else query.lower()
        
        for root, dirs, files in os.walk(search_dir):
            for file in files:
                if len(results) >= max_results:
                    break
                
                file_path = os.path.join(root, file)
                
                try:
                    # 检查文件内容
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                    # 搜索匹配
                    if case_sensitive:
                        matches = content.count(search_pattern)
                    else:
                        matches = content.lower().count(search_pattern)
                    
                    if matches > 0:
                        # 提取上下文
                        context_lines = self._extract_context(content, search_pattern, case_sensitive)
                        
                        results.append({
                            'file_path': file_path,
                            'file_name': file,
                            'matches': matches,
                            'context': context_lines,
                            'relative_path': os.path.relpath(file_path, search_dir)
                        })
                        
                except (IOError, UnicodeDecodeError):
                    # 跳过无法读取的文件
                    continue
        
        return results
    
    def _regex_search(self, pattern: str, case_sensitive: bool, max_results: int) -> List[Dict[str, Any]]:
        """正则表达式搜索"""
        
        results = []
        search_dir = os.getcwd()
        
        # 编译正则表达式
        flags = 0 if case_sensitive else re.IGNORECASE
        
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            raise ValueError(f"无效的正则表达式: {str(e)}")
        
        for root, dirs, files in os.walk(search_dir):
            for file in files:
                if len(results) >= max_results:
                    break
                
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # 搜索匹配
                    matches = list(regex.finditer(content))
                    
                    if matches:
                        # 提取匹配上下文
                        context_lines = []
                        for match in matches[:3]:  # 最多显示3个匹配的上下文
                            start, end = match.span()
                            context = self._extract_regex_context(content, start, end)
                            context_lines.append({
                                'match_text': match.group(),
                                'context': context,
                                'position': start
                            })
                        
                        results.append({
                            'file_path': file_path,
                            'file_name': file,
                            'matches_count': len(matches),
                            'context': context_lines,
                            'relative_path': os.path.relpath(file_path, search_dir)
                        })
                        
                except (IOError, UnicodeDecodeError):
                    continue
        
        return results
    
    def _extract_context(self, content: str, pattern: str, case_sensitive: bool, 
                        context_lines: int = 3) -> List[str]:
        """提取匹配内容的上下文"""
        
        lines = content.split('\n')
        context = []
        
        search_content = content if case_sensitive else content.lower()
        search_pattern = pattern if case_sensitive else pattern.lower()
        
        # 查找匹配行
        for i, line in enumerate(lines):
            line_to_search = line if case_sensitive else line.lower()
            
            if search_pattern in line_to_search:
                # 添加上下文行
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                
                for j in range(start, end):
                    context_line = f"{j+1}: {lines[j]}"
                    if j == i:
                        context_line = f"> {context_line}"  # 标记匹配行
                    context.append(context_line)
                
                context.append("---")  # 分隔符
        
        return context[:20]  # 限制返回的行数
    
    def _extract_regex_context(self, content: str, start: int, end: int, 
                              context_chars: int = 100) -> str:
        """提取正则匹配的上下文"""
        
        # 计算上下文范围
        context_start = max(0, start - context_chars)
        context_end = min(len(content), end + context_chars)
        
        context = content[context_start:context_end]
        
        # 标记匹配部分
        match_start = start - context_start
        match_end = end - context_start
        
        marked_context = (
            context[:match_start] + 
            f"【{context[match_start:match_end]}】" + 
            context[match_end:]
        )
        
        return marked_context
    
    def get_search_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取搜索历史"""
        return self.search_history[-limit:]
    
    def clear_search_history(self) -> None:
        """清空搜索历史"""
        self.search_history.clear()
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


class AdvancedSearchTool(SearchTool):
    """高级搜索工具 - 扩展功能"""
    
    def __init__(self):
        super().__init__()
        self.name = "advanced_search"
        self.description = "高级搜索工具，支持过滤、排序和多种搜索策略"
        
        # 扩展参数定义
        self.parameters["properties"].update({
            "filters": {
                "type": "object",
                "description": "过滤器配置",
                "properties": {
                    "file_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "文件类型过滤，如 ['.py', '.txt']"
                    },
                    "path_pattern": {
                        "type": "string",
                        "description": "路径模式过滤"
                    },
                    "min_matches": {
                        "type": "integer",
                        "description": "最小匹配数量"
                    },
                    "max_file_size_kb": {
                        "type": "integer",
                        "description": "最大文件大小（KB）"
                    }
                }
            },
            "sort_by": {
                "type": "string",
                "description": "排序方式：relevance（相关性）、filename（文件名）、path（路径）、file_size（文件大小）",
                "enum": ["relevance", "filename", "path", "file_size"],
                "default": "relevance"
            },
            "search_strategy": {
                "type": "string",
                "description": "搜索策略：breadth_first（广度优先）、depth_first（深度优先）、recent_first（最近优先）",
                "enum": ["breadth_first", "depth_first", "recent_first"],
                "default": "breadth_first"
            }
        })
    
    def execute(self, query: str, search_type: str = "text",
               filters: Optional[Dict[str, Any]] = None,
               sort_by: str = "relevance",
               search_strategy: str = "breadth_first") -> Dict[str, Any]:
        """执行高级搜索"""
        
        try:
            # 先执行基础搜索
            base_results = super().execute(query, search_type, False, 50)
            
            if not base_results.get("success", False):
                return base_results
            
            # 应用过滤器
            filtered_results = self._apply_filters(base_results['results'], filters or {})
            
            # 排序结果
            sorted_results = self._sort_results(filtered_results, sort_by)
            
            # 应用搜索策略
            final_results = self._apply_search_strategy(sorted_results, search_strategy)
            
            # 记录高级搜索
            search_record = {
                'query': query,
                'type': search_type,
                'filters': filters,
                'sort_by': sort_by,
                'strategy': search_strategy,
                'original_count': len(base_results['results']),
                'filtered_count': len(final_results),
                'timestamp': self._get_timestamp()
            }
            self.search_history.append(search_record)
            
            return {
                "success": True,
                "query": query,
                "search_type": search_type,
                "filters_applied": filters,
                "sort_by": sort_by,
                "search_strategy": search_strategy,
                "results": final_results,
                "total_original": len(base_results['results']),
                "total_filtered": len(final_results),
                "filtering_efficiency": len(final_results) / len(base_results['results']) if base_results['results'] else 0,
                "search_id": len(self.search_history)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "search_type": search_type,
                "results": [],
                "total_results": 0
            }
    
    def _apply_filters(self, results: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """应用过滤器"""
        
        filtered_results = results.copy()
        
        # 文件类型过滤
        if 'file_types' in filters:
            allowed_extensions = [ext.strip().lower() for ext in filters['file_types']]
            filtered_results = [
                r for r in filtered_results 
                if any(r['file_name'].lower().endswith(ext) for ext in allowed_extensions)
            ]
        
        # 路径过滤
        if 'path_pattern' in filters:
            pattern = filters['path_pattern'].lower()
            filtered_results = [
                r for r in filtered_results 
                if pattern in r['file_path'].lower() or pattern in r['relative_path'].lower()
            ]
        
        # 匹配数量过滤
        if 'min_matches' in filters:
            min_matches = filters['min_matches']
            filtered_results = [
                r for r in filtered_results 
                if r.get('matches', r.get('matches_count', 0)) >= min_matches
            ]
        
        # 文件大小过滤（如果可用）
        if 'max_file_size_kb' in filters:
            max_size = filters['max_file_size_kb'] * 1024  # 转换为字节
            filtered_results = [
                r for r in filtered_results 
                if os.path.getsize(r['file_path']) <= max_size
            ]
        
        return filtered_results
    
    def _sort_results(self, results: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        """排序结果"""
        
        if sort_by == "relevance":
            # 按匹配数量降序排序
            return sorted(results, key=lambda x: x.get('matches', x.get('matches_count', 0)), reverse=True)
        
        elif sort_by == "filename":
            # 按文件名排序
            return sorted(results, key=lambda x: x['file_name'])
        
        elif sort_by == "path":
            # 按路径排序
            return sorted(results, key=lambda x: x['relative_path'])
        
        elif sort_by == "file_size":
            # 按文件大小排序
            return sorted(results, key=lambda x: os.path.getsize(x['file_path']))
        
        else:
            # 默认按相关性排序
            return sorted(results, key=lambda x: x.get('matches', x.get('matches_count', 0)), reverse=True)
    
    def _apply_search_strategy(self, results: List[Dict[str, Any]], strategy: str) -> List[Dict[str, Any]]:
        """应用搜索策略"""
        
        if strategy == "depth_first":
            # 深度优先：优先处理单个文件的多个匹配
            return sorted(results, key=lambda x: x.get('matches', x.get('matches_count', 0)), reverse=True)
        
        elif strategy == "breadth_first":
            # 广度优先：尽可能覆盖更多文件
            return results  # 保持原顺序
        
        elif strategy == "recent_first":
            # 最近修改优先
            return sorted(results, key=lambda x: os.path.getmtime(x['file_path']), reverse=True)
        
        else:
            return results
    
    def search_with_patterns(self, patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """使用多个模式进行搜索"""
        
        all_results = {}
        
        for pattern_info in patterns:
            pattern = pattern_info['pattern']
            search_type = pattern_info.get('type', 'text')
            
            try:
                result = self.execute(pattern, search_type)
                all_results[pattern] = result
            except Exception as e:
                all_results[pattern] = {'error': str(e)}
        
        # 分析交叉匹配
        cross_analysis = self._analyze_cross_matches(all_results)
        
        return {
            'pattern_results': all_results,
            'cross_analysis': cross_analysis,
            'total_patterns': len(patterns),
            'successful_searches': sum(1 for r in all_results.values() if 'error' not in r)
        }
    
    def _analyze_cross_matches(self, pattern_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析交叉匹配"""
        
        # 收集所有匹配的文件
        all_files = set()
        pattern_files = {}
        
        for pattern, result in pattern_results.items():
            if 'error' not in result and 'results' in result:
                files = [r['file_path'] for r in result['results']]
                pattern_files[pattern] = set(files)
                all_files.update(files)
        
        # 分析文件被多个模式匹配的情况
        file_pattern_counts = {}
        for file_path in all_files:
            matching_patterns = [
                pattern for pattern, files in pattern_files.items() 
                if file_path in files
            ]
            file_pattern_counts[file_path] = len(matching_patterns)
        
        # 统计
        analysis = {
            'total_files': len(all_files),
            'files_with_single_pattern': sum(1 for count in file_pattern_counts.values() if count == 1),
            'files_with_multiple_patterns': sum(1 for count in file_pattern_counts.values() if count > 1),
            'max_patterns_per_file': max(file_pattern_counts.values()) if file_pattern_counts else 0,
            'pattern_coverage': {}
        }
        
        # 模式覆盖率
        for pattern, files in pattern_files.items():
            analysis['pattern_coverage'][pattern] = {
                'files_matched': len(files),
                'coverage_percent': len(files) / len(all_files) if all_files else 0
            }
        
        return analysis