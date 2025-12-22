"""
评估器 - 评估知识检索效果和Agent性能
提供质量监控和优化建议
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


class KnowledgeEvaluator:
    """知识检索评估器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.evaluation_history: List[Dict[str, Any]] = []
        self.metrics = {
            'retrieval_accuracy': 0.0,
            'response_relevance': 0.0,
            'latency_ms': 0.0,
            'success_rate': 0.0
        }
    
    async def evaluate_retrieval_performance(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        expected_results: Optional[List[str]] = None,
        execution_time_ms: float = 0.0
    ) -> Dict[str, Any]:
        """评估检索性能"""
        
        evaluation = {
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'metrics': {},
            'suggestions': []
        }
        
        # 1. 计算检索准确率
        if expected_results:
            accuracy = self._calculate_retrieval_accuracy(retrieved_chunks, expected_results)
            evaluation['metrics']['retrieval_accuracy'] = accuracy
        
        # 2. 计算响应相关性
        relevance_score = self._calculate_relevance_score(query, retrieved_chunks)
        evaluation['metrics']['response_relevance'] = relevance_score
        
        # 3. 记录延迟
        evaluation['metrics']['latency_ms'] = execution_time_ms
        
        # 4. 计算成功率
        success_rate = 1.0 if retrieved_chunks else 0.0
        evaluation['metrics']['success_rate'] = success_rate
        
        # 5. 生成优化建议
        suggestions = self._generate_optimization_suggestions(evaluation['metrics'])
        evaluation['suggestions'] = suggestions
        
        # 6. 更新历史记录
        self.evaluation_history.append(evaluation)
        
        # 7. 更新总体指标
        self._update_overall_metrics(evaluation['metrics'])
        
        return evaluation
    
    async def evaluate_agent_performance(
        self,
        agent_id: str,
        user_input: str,
        agent_response: Dict[str, Any],
        execution_time_ms: float = 0.0
    ) -> Dict[str, Any]:
        """评估Agent性能"""
        
        evaluation = {
            'agent_id': agent_id,
            'user_input': user_input,
            'timestamp': datetime.now().isoformat(),
            'metrics': {},
            'improvements': []
        }
        
        # 1. 响应质量评估
        quality_score = self._evaluate_response_quality(agent_response)
        evaluation['metrics']['response_quality'] = quality_score
        
        # 2. 知识利用评估
        knowledge_utilization = self._evaluate_knowledge_utilization(agent_response)
        evaluation['metrics']['knowledge_utilization'] = knowledge_utilization
        
        # 3. 执行效率
        evaluation['metrics']['execution_time_ms'] = execution_time_ms
        
        # 4. 置信度分析
        confidence_score = agent_response.get('confidence', 0.0)
        evaluation['metrics']['confidence'] = confidence_score
        
        # 5. 生成改进建议
        improvements = self._generate_agent_improvements(evaluation['metrics'])
        evaluation['improvements'] = improvements
        
        return evaluation
    
    def _calculate_retrieval_accuracy(
        self, 
        retrieved_chunks: List[Dict[str, Any]], 
        expected_results: List[str]
    ) -> float:
        """计算检索准确率"""
        if not retrieved_chunks or not expected_results:
            return 0.0
        
        # 简单的关键词匹配准确率
        retrieved_content = ' '.join([chunk.get('content', '') for chunk in retrieved_chunks])
        
        matched_keywords = 0
        for keyword in expected_results:
            if keyword.lower() in retrieved_content.lower():
                matched_keywords += 1
        
        return matched_keywords / len(expected_results) if expected_results else 0.0
    
    def _calculate_relevance_score(self, query: str, retrieved_chunks: List[Dict[str, Any]]) -> float:
        """计算响应相关性得分"""
        if not retrieved_chunks:
            return 0.0
        
        query_words = set(query.lower().split())
        total_relevance = 0.0
        
        for chunk in retrieved_chunks:
            content = chunk.get('content', '').lower()
            chunk_words = set(content.split())
            
            # 计算查询词覆盖率
            intersection = query_words.intersection(chunk_words)
            coverage = len(intersection) / len(query_words) if query_words else 0.0
            
            # 考虑分数权重
            score = chunk.get('score', 0.0)
            relevance = coverage * 0.7 + score * 0.3
            total_relevance += relevance
        
        return total_relevance / len(retrieved_chunks) if retrieved_chunks else 0.0
    
    def _evaluate_response_quality(self, response: Dict[str, Any]) -> float:
        """评估响应质量"""
        quality_score = 0.0
        
        # 1. 内容完整性
        content = response.get('content', '')
        if content:
            quality_score += 0.3  # 基础分
            
            # 内容长度适中加分
            content_length = len(content)
            if 50 <= content_length <= 500:
                quality_score += 0.2
            elif content_length > 500:
                quality_score += 0.1
        
        # 2. 结构化程度
        if response.get('sources'):
            quality_score += 0.2
        
        # 3. 置信度
        confidence = response.get('confidence', 0.0)
        quality_score += confidence * 0.3
        
        return min(quality_score, 1.0)
    
    def _evaluate_knowledge_utilization(self, response: Dict[str, Any]) -> float:
        """评估知识利用程度"""
        utilization_score = 0.0
        
        # 检查是否有引用知识来源
        sources = response.get('sources', [])
        if sources:
            utilization_score += 0.5
            
            # 来源多样性加分
            unique_sources = len(set(sources))
            if unique_sources >= 2:
                utilization_score += 0.3
            if unique_sources >= 3:
                utilization_score += 0.2
        
        # 检查是否有知识上下文
        if response.get('knowledge_context'):
            utilization_score += 0.2
        
        return min(utilization_score, 1.0)
    
    def _generate_optimization_suggestions(self, metrics: Dict[str, Any]) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        if metrics.get('retrieval_accuracy', 0.0) < 0.7:
            suggestions.append("建议优化检索策略，提高查询准确性")
        
        if metrics.get('response_relevance', 0.0) < 0.6:
            suggestions.append("建议调整重排序算法，提高结果相关性")
        
        if metrics.get('latency_ms', 0.0) > 1000:
            suggestions.append("建议优化向量搜索性能，减少延迟")
        
        if metrics.get('success_rate', 0.0) < 0.8:
            suggestions.append("建议增加错误处理和降级策略")
        
        return suggestions
    
    def _generate_agent_improvements(self, metrics: Dict[str, Any]) -> List[str]:
        """生成Agent改进建议"""
        improvements = []
        
        if metrics.get('response_quality', 0.0) < 0.7:
            improvements.append("建议优化Agent的响应生成逻辑")
        
        if metrics.get('knowledge_utilization', 0.0) < 0.5:
            improvements.append("建议加强知识上下文的利用")
        
        if metrics.get('execution_time_ms', 0.0) > 5000:
            improvements.append("建议优化Agent的执行效率")
        
        if metrics.get('confidence', 0.0) < 0.6:
            improvements.append("建议提高Agent的置信度评估准确性")
        
        return improvements
    
    def _update_overall_metrics(self, current_metrics: Dict[str, Any]) -> None:
        """更新总体指标"""
        # 简单的滑动平均更新
        alpha = 0.1  # 学习率
        
        for metric_name, current_value in current_metrics.items():
            if metric_name in self.metrics:
                old_value = self.metrics[metric_name]
                self.metrics[metric_name] = (1 - alpha) * old_value + alpha * current_value
    
    def get_performance_report(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """获取性能报告"""
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        
        recent_evaluations = [
            eval_data for eval_data in self.evaluation_history
            if datetime.fromisoformat(eval_data['timestamp']) >= cutoff_time
        ]
        
        return {
            'time_window_hours': time_window_hours,
            'total_evaluations': len(recent_evaluations),
            'average_metrics': self.metrics,
            'recent_trend': self._calculate_recent_trend(recent_evaluations),
            'recommendations': self._generate_performance_recommendations()
        }
    
    def _calculate_recent_trend(self, recent_evaluations: List[Dict[str, Any]]) -> str:
        """计算近期趋势"""
        if len(recent_evaluations) < 2:
            return "数据不足"
        
        # 简单趋势分析
        first_half = recent_evaluations[:len(recent_evaluations)//2]
        second_half = recent_evaluations[len(recent_evaluations)//2:]
        
        first_avg = self._calculate_average_metrics(first_half)
        second_avg = self._calculate_average_metrics(second_half)
        
        improvement_count = 0
        for metric in first_avg.keys():
            if second_avg.get(metric, 0) > first_avg.get(metric, 0):
                improvement_count += 1
        
        if improvement_count >= len(first_avg) // 2:
            return "改善中"
        elif improvement_count <= len(first_avg) // 4:
            return "下降中"
        else:
            return "稳定"
    
    def _calculate_average_metrics(self, evaluations: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算平均指标"""
        if not evaluations:
            return {}
        
        avg_metrics = {}
        metric_counts = {}
        
        for eval_data in evaluations:
            for metric_name, value in eval_data.get('metrics', {}).items():
                if metric_name not in avg_metrics:
                    avg_metrics[metric_name] = 0.0
                    metric_counts[metric_name] = 0
                
                avg_metrics[metric_name] += value
                metric_counts[metric_name] += 1
        
        for metric_name in avg_metrics:
            avg_metrics[metric_name] /= metric_counts[metric_name]
        
        return avg_metrics
    
    def _generate_performance_recommendations(self) -> List[str]:
        """生成性能优化建议"""
        recommendations = []
        
        if self.metrics['retrieval_accuracy'] < 0.8:
            recommendations.append("考虑使用更先进的嵌入模型")
        
        if self.metrics['response_relevance'] < 0.7:
            recommendations.append("优化混合检索的权重配置")
        
        if self.metrics['latency_ms'] > 800:
            recommendations.append("考虑使用缓存机制优化性能")
        
        if self.metrics['success_rate'] < 0.9:
            recommendations.append("加强错误处理和重试机制")
        
        return recommendations