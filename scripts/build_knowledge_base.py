#!/usr/bin/env python3
"""
知识库构建脚本
批量构建和更新知识库
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KnowledgeBaseBuilder:
    """知识库构建器"""
    
    def __init__(self):
        self.knowledge_bases: Dict[str, Any] = {}
    
    async def build_code_knowledge_base(self) -> None:
        """构建代码知识库"""
        logger.info("开始构建代码知识库")
        
        # 1. 扫描项目代码
        code_files = await self.scan_code_files()
        
        # 2. 处理代码文档
        processed_docs = await self.process_code_documents(code_files)
        
        # 3. 构建知识库
        await self.build_knowledge_base('code_knowledge', processed_docs)
        
        logger.info("代码知识库构建完成")
    
    async def build_general_knowledge_base(self) -> None:
        """构建通用知识库"""
        logger.info("开始构建通用知识库")
        
        # 1. 扫描文档文件
        doc_files = await self.scan_document_files()
        
        # 2. 处理文档
        processed_docs = await self.process_general_documents(doc_files)
        
        # 3. 构建知识库
        await self.build_knowledge_base('general_knowledge', processed_docs)
        
        logger.info("通用知识库构建完成")
    
    async def scan_code_files(self) -> List[Path]:
        """扫描代码文件"""
        code_extensions = {'.py', '.js', '.java', '.cpp', '.c', '.h', '.html', '.css'}
        code_files = []
        
        # 扫描项目根目录
        project_root = Path(__file__).parent.parent
        
        for ext in code_extensions:
            files = list(project_root.rglob(f'*{ext}'))
            code_files.extend(files)
        
        # 过滤掉一些不需要的文件
        filtered_files = []
        exclude_patterns = ['__pycache__', '.git', 'node_modules', 'dist', 'build']
        
        for file_path in code_files:
            if not any(pattern in str(file_path) for pattern in exclude_patterns):
                filtered_files.append(file_path)
        
        logger.info(f"扫描到 {len(filtered_files)} 个代码文件")
        return filtered_files
    
    async def scan_document_files(self) -> List[Path]:
        """扫描文档文件"""
        doc_extensions = {'.md', '.txt', '.rst', '.pdf', '.docx'}
        doc_files = []
        
        # 扫描文档目录
        docs_dir = Path(__file__).parent.parent / 'docs'
        knowledge_data_dir = Path(__file__).parent.parent / 'knowledge'
        
        search_dirs = [docs_dir, knowledge_data_dir]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                for ext in doc_extensions:
                    files = list(search_dir.rglob(f'*{ext}'))
                    doc_files.extend(files)
        
        logger.info(f"扫描到 {len(doc_files)} 个文档文件")
        return doc_files
    
    async def process_code_documents(self, code_files: List[Path]) -> List[Dict[str, Any]]:
        """处理代码文档"""
        documents = []
        
        for file_path in code_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                
                document = {
                    'content': content,
                    'metadata': {
                        'type': 'code',
                        'language': self._detect_language(file_path),
                        'file_path': str(file_path),
                        'file_size': len(content),
                        'lines': content.count('\n') + 1
                    }
                }
                
                documents.append(document)
                logger.debug(f"处理代码文件: {file_path}")
                
            except Exception as e:
                logger.warning(f"处理文件失败 {file_path}: {str(e)}")
        
        logger.info(f"成功处理 {len(documents)} 个代码文档")
        return documents
    
    async def process_general_documents(self, doc_files: List[Path]) -> List[Dict[str, Any]]:
        """处理通用文档"""
        documents = []
        
        for file_path in doc_files:
            try:
                if file_path.suffix == '.md':
                    content = file_path.read_text(encoding='utf-8')
                else:
                    # TODO: 支持其他格式的文档解析
                    content = f"文档内容: {file_path.name}"
                
                document = {
                    'content': content,
                    'metadata': {
                        'type': 'document',
                        'format': file_path.suffix,
                        'file_path': str(file_path),
                        'file_size': len(content)
                    }
                }
                
                documents.append(document)
                logger.debug(f"处理文档文件: {file_path}")
                
            except Exception as e:
                logger.warning(f"处理文件失败 {file_path}: {str(e)}")
        
        logger.info(f"成功处理 {len(documents)} 个通用文档")
        return documents
    
    async def build_knowledge_base(self, kb_name: str, documents: List[Dict[str, Any]]) -> None:
        """构建知识库"""
        logger.info(f"开始构建知识库: {kb_name}")
        
        # TODO: 实现知识库构建逻辑
        # 需要创建KnowledgeBase实例并添加文档
        
        logger.info(f"知识库 '{kb_name}' 构建完成，包含 {len(documents)} 个文档")
    
    def _detect_language(self, file_path: Path) -> str:
        """检测编程语言"""
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c_header',
            '.html': 'html',
            '.css': 'css'
        }
        
        return extension_map.get(file_path.suffix, 'unknown')
    
    async def run_full_build(self) -> None:
        """运行完整构建流程"""
        logger.info("开始完整知识库构建流程")
        
        try:
            # 1. 构建代码知识库
            await self.build_code_knowledge_base()
            
            # 2. 构建通用知识库
            await self.build_general_knowledge_base()
            
            # 3. 生成构建报告
            await self.generate_build_report()
            
            logger.info("知识库构建流程完成")
            
        except Exception as e:
            logger.error(f"构建流程失败: {str(e)}")
            raise
    
    async def generate_build_report(self) -> None:
        """生成构建报告"""
        report = {
            'timestamp': self._get_timestamp(),
            'knowledge_bases': list(self.knowledge_bases.keys()),
            'total_documents': sum(len(docs) for docs in self.knowledge_bases.values()),
            'status': 'completed'
        }
        
        # 保存报告
        report_file = Path(__file__).parent.parent / 'knowledge' / 'build_report.json'
        
        import json
        report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        
        logger.info(f"构建报告已保存到: {report_file}")
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


async def main():
    """主函数"""
    builder = KnowledgeBaseBuilder()
    await builder.run_full_build()


if __name__ == '__main__':
    asyncio.run(main())