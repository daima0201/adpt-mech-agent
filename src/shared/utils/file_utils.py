"""
文件操作工具
提供统一的文件读写和目录管理功能
"""

import json
import yaml
import pickle
from pathlib import Path
from typing import Any, Dict, List, Union, Optional
import shutil


def read_file(file_path: Union[str, Path], encoding: str = 'utf-8') -> str:
    """
    读取文本文件内容
    
    Args:
        file_path: 文件路径
        encoding: 文件编码
        
    Returns:
        文件内容字符串
        
    Raises:
        FileNotFoundError: 文件不存在
        IOError: 读取失败
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    try:
        with open(path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        raise IOError(f"读取文件失败 {file_path}: {str(e)}")


def write_file(
    file_path: Union[str, Path], 
    content: str, 
    encoding: str = 'utf-8',
    create_dirs: bool = True
) -> None:
    """
    写入文本文件
    
    Args:
        file_path: 文件路径
        content: 要写入的内容
        encoding: 文件编码
        create_dirs: 是否自动创建目录
        
    Raises:
        IOError: 写入失败
    """
    path = Path(file_path)
    
    if create_dirs:
        ensure_directory(path.parent)
    
    try:
        with open(path, 'w', encoding=encoding) as f:
            f.write(content)
    except Exception as e:
        raise IOError(f"写入文件失败 {file_path}: {str(e)}")


def read_json(file_path: Union[str, Path]) -> Union[Dict, List]:
    """
    读取JSON文件
    
    Args:
        file_path: JSON文件路径
        
    Returns:
        JSON解析后的数据
        
    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON格式错误
    """
    content = read_file(file_path)
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"JSON解析失败 {file_path}: {str(e)}", e.doc, e.pos)


def write_json(
    file_path: Union[str, Path], 
    data: Union[Dict, List],
    indent: int = 2,
    ensure_ascii: bool = False
) -> None:
    """
    写入JSON文件
    
    Args:
        file_path: JSON文件路径
        data: 要写入的数据
        indent: 缩进空格数
        ensure_ascii: 是否确保ASCII编码
        
    Raises:
        IOError: 写入失败
    """
    try:
        json_str = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)
        write_file(file_path, json_str)
    except Exception as e:
        raise IOError(f"写入JSON文件失败 {file_path}: {str(e)}")


def read_yaml(file_path: Union[str, Path]) -> Union[Dict, List]:
    """
    读取YAML文件
    
    Args:
        file_path: YAML文件路径
        
    Returns:
        YAML解析后的数据
        
    Raises:
        FileNotFoundError: 文件不存在
        yaml.YAMLError: YAML格式错误
    """
    content = read_file(file_path)
    try:
        return yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"YAML解析失败 {file_path}: {str(e)}")


def write_yaml(file_path: Union[str, Path], data: Union[Dict, List]) -> None:
    """
    写入YAML文件
    
    Args:
        file_path: YAML文件路径
        data: 要写入的数据
        
    Raises:
        IOError: 写入失败
    """
    try:
        yaml_str = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        write_file(file_path, yaml_str)
    except Exception as e:
        raise IOError(f"写入YAML文件失败 {file_path}: {str(e)}")


def read_pickle(file_path: Union[str, Path]) -> Any:
    """
    读取pickle文件
    
    Args:
        file_path: pickle文件路径
        
    Returns:
        反序列化的对象
        
    Raises:
        FileNotFoundError: 文件不存在
        pickle.UnpicklingError: 反序列化失败
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    try:
        with open(path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        raise pickle.UnpicklingError(f"读取pickle文件失败 {file_path}: {str(e)}")


def write_pickle(file_path: Union[str, Path], obj: Any) -> None:
    """
    写入pickle文件
    
    Args:
        file_path: pickle文件路径
        obj: 要序列化的对象
        
    Raises:
        IOError: 写入失败
    """
    path = Path(file_path)
    ensure_directory(path.parent)
    
    try:
        with open(path, 'wb') as f:
            pickle.dump(obj, f)
    except Exception as e:
        raise IOError(f"写入pickle文件失败 {file_path}: {str(e)}")


def ensure_directory(directory: Union[str, Path]) -> None:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
        
    Raises:
        IOError: 创建目录失败
    """
    path = Path(directory)
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise IOError(f"创建目录失败 {directory}: {str(e)}")


def list_files(
    directory: Union[str, Path], 
    pattern: str = "*",
    recursive: bool = False
) -> List[Path]:
    """
    列出目录中的文件
    
    Args:
        directory: 目录路径
        pattern: 文件匹配模式
        recursive: 是否递归搜索
        
    Returns:
        文件路径列表
        
    Raises:
        FileNotFoundError: 目录不存在
    """
    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(f"目录不存在: {directory}")
    
    if recursive:
        return list(path.rglob(pattern))
    else:
        return list(path.glob(pattern))


def copy_file(source: Union[str, Path], destination: Union[str, Path]) -> None:
    """
    复制文件
    
    Args:
        source: 源文件路径
        destination: 目标文件路径
        
    Raises:
        FileNotFoundError: 源文件不存在
        IOError: 复制失败
    """
    src_path = Path(source)
    dst_path = Path(destination)
    
    if not src_path.exists():
        raise FileNotFoundError(f"源文件不存在: {source}")
    
    ensure_directory(dst_path.parent)
    
    try:
        shutil.copy2(src_path, dst_path)
    except Exception as e:
        raise IOError(f"复制文件失败 {source} -> {destination}: {str(e)}")


def delete_file(file_path: Union[str, Path]) -> None:
    """
    删除文件
    
    Args:
        file_path: 文件路径
        
    Raises:
        FileNotFoundError: 文件不存在
        IOError: 删除失败
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    try:
        path.unlink()
    except Exception as e:
        raise IOError(f"删除文件失败 {file_path}: {str(e)}")


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    获取文件大小（字节）
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件大小（字节）
        
    Raises:
        FileNotFoundError: 文件不存在
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    return path.stat().st_size


def get_file_extension(file_path: Union[str, Path]) -> str:
    """
    获取文件扩展名
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件扩展名（小写，包含点）
    """
    path = Path(file_path)
    return path.suffix.lower()