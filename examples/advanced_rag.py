#!/usr/bin/env python3
"""
高级RAG功能示例
演示知识库的高级检索功能
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.knowledge.core.knowledge_base import KnowledgeBase
from src.knowledge.retrievers.hybrid_retriever import HybridRetriever
from src.knowledge.retrievers.reranker import Reranker
from src.shared.config.manager import ConfigManager
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


def demonstrate_basic_retrieval(kb):
    """演示基础检索功能"""
    print("\n=== 基础向量检索 ===")
    
    queries = [
        "Agent架构设计",
        "知识库使用方法", 
        "RAG工作原理"
    ]
    
    for query in queries:
        print(f"\n查询: {query}")
        results = kb.search(query, top_k=3)
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. 相似度: {result.score:.3f}")
            print(f"     内容: {result.content[:100]}...")
            print(f"     来源: {result.metadata.get('source', 'Unknown')}")


def demonstrate_hybrid_retrieval(kb):
    """演示混合检索功能"""
    print("\n=== 混合检索（向量+关键词）===")
    
    # 获取混合检索器
    hybrid_retriever = kb.retriever
    if isinstance(hybrid_retriever, HybridRetriever):
        query = "如何配置Agent工具"
        print(f"查询: {query}")
        
        # 分别测试不同检索方式
        vector_results = hybrid_retriever.vector_retriever.retrieve(query, top_k=5)
        keyword_results = hybrid_retriever.keyword_retriever.retrieve(query, top_k=5)
        
        print("\n向量检索结果:")
        for i, result in enumerate(vector_results[:3], 1):
            print(f"  {i}. {result.content[:80]}...")
        
        print("\n关键词检索结果:")
        for i, result in enumerate(keyword_results[:3], 1):
            print(f"  {i}. {result.content[:80]}...")
        
        # 混合检索结果
        hybrid_results = hybrid_retriever.retrieve(query, top_k=5)
        print("\n混合检索结果:")
        for i, result in enumerate(hybrid_results, 1):
            print(f"  {i}. 分数: {result.score:.3f}")
            print(f"     内容: {result.content[:100]}...")


def demonstrate_reranking(kb):
    """演示重排序功能"""
    print("\n=== 重排序功能 ===")
    
    query = "项目部署指南"
    print(f"查询: {query}")
    
    # 先进行基础检索
    initial_results = kb.search(query, top_k=10)
    
    print("\n初始检索结果:")
    for i, result in enumerate(initial_results[:5], 1):
        print(f"  {i}. 相似度: {result.score:.3f}")
        print(f"     内容: {result.content[:80]}...")
    
    # 应用重排序
    reranker = Reranker()
    reranked_results = reranker.rerank(query, initial_results)
    
    print("\n重排序后结果:")
    for i, result in enumerate(reranked_results[:5], 1):
        print(f"  {i}. 重排序分数: {result.rerank_score:.3f}")
        print(f"     内容: {result.content[:80]}...")


def demonstrate_metadata_filtering(kb):
    """演示元数据过滤功能"""
    print("\n=== 元数据过滤 ===")
    
    # 构建带过滤条件的查询
    query = "配置管理"
    filters = {
        "file_type": "yaml",  # 只搜索YAML文件
        "category": "config"  # 配置相关文档
    }
    
    print(f"查询: {query}")
    print(f"过滤条件: {filters}")
    
    try:
        # 使用带过滤的检索
        filtered_results = kb.search_with_filters(query, filters=filters, top_k=5)
        
        for i, result in enumerate(filtered_results, 1):
            print(f"  {i}. 相似度: {result.score:.3f}")
            print(f"     内容: {result.content[:100]}...")
            print(f"     元数据: {result.metadata}")
    except Exception as e:
        print(f"  注意: 元数据过滤功能需要相应的元数据支持 - {e}")


def demonstrate_multilingual_search(kb):
    """演示多语言搜索功能"""
    print("\n=== 多语言搜索 ===")
    
    multilingual_queries = [
        "What is RAG architecture?",  # 英文
        "¿Cómo funciona el RAG?",     # 西班牙文
        "RAG是如何工作的？",           # 中文
        "RAGの仕組みは？"             # 日文
    ]
    
    for query in multilingual_queries:
        print(f"\n查询: {query}")
        results = kb.search(query, top_k=2)
        
        for i, result in enumerate(results, 1):
            print(f"  {i}. 相似度: {result.score:.3f}")
            print(f"     内容: {result.content[:80]}...")


def main():
    """主函数"""
    print("=== 高级RAG功能示例 ===")
    
    try:
        # 1. 加载配置和知识库
        config = ConfigManager().get_config()
        kb = KnowledgeBase(config)
        
        # 检查知识库状态
        if not kb.is_initialized():
            print("知识库未初始化，请先运行 build_knowledge_base.py")
            return
        
        print(f"知识库已初始化，包含 {kb.get_document_count()} 个文档")
        
        # 2. 演示各种检索功能
        demonstrate_basic_retrieval(kb)
        demonstrate_hybrid_retrieval(kb)
        demonstrate_reranking(kb)
        demonstrate_metadata_filtering(kb)
        demonstrate_multilingual_search(kb)
        
        print("\n=== 示例完成 ===")
        
    except Exception as e:
        logger.error(f"示例执行失败: {e}")
        print(f"错误: {e}")


if __name__ == "__main__":
    main()