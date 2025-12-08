#!/usr/bin/env python3
"""
知识感知Agent使用示例
演示如何将知识库与Agent结合使用
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.impls.react_agent import ReActAgent
from src.knowledge.core.knowledge_base import KnowledgeBase
from src.shared.config.manager import ConfigManager
from src.shared.utils.logger import get_logger

logger = get_logger(__name__)


def setup_knowledge_base():
    """设置知识库"""
    config = ConfigManager().get_config()
    
    # 初始化知识库
    kb = KnowledgeBase(config)
    
    # 检查知识库是否已构建
    if not kb.is_initialized():
        logger.info("知识库未初始化，开始构建...")
        kb.build_from_directory(config.paths.knowledge_base)
        logger.info("知识库构建完成")
    
    return kb


def create_knowledge_aware_agent(kb):
    """创建知识感知Agent"""
    config = ConfigManager().get_config()
    
    # 创建ReAct Agent（支持知识检索）
    agent = ReActAgent(config, knowledge_base=kb)
    
    return agent


def run_example_queries(agent):
    """运行示例查询"""
    queries = [
        "请介绍一下这个项目的架构设计",
        "如何使用知识库功能？",
        "解释一下RAG的工作原理",
        "如何自定义Agent工具？",
        "项目的部署方式有哪些？"
    ]
    
    for query in queries:
        print(f"\n{'='*50}")
        print(f"查询: {query}")
        print('-'*50)
        
        try:
            response = agent.process_message(query)
            print(f"回答: {response}")
        except Exception as e:
            print(f"错误: {e}")


def main():
    """主函数"""
    print("=== 知识感知Agent示例 ===")
    
    try:
        # 1. 设置知识库
        print("步骤1: 初始化知识库...")
        kb = setup_knowledge_base()
        
        # 2. 创建Agent
        print("步骤2: 创建知识感知Agent...")
        agent = create_knowledge_aware_agent(kb)
        
        # 3. 运行示例查询
        print("步骤3: 运行示例查询...")
        run_example_queries(agent)
        
        print("\n=== 示例完成 ===")
        
    except Exception as e:
        logger.error(f"示例执行失败: {e}")
        print(f"错误: {e}")


if __name__ == "__main__":
    main()