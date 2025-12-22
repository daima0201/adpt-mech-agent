"""
内置计算器工具
提供数学计算功能
"""

import math
import re
from typing import Dict, Any, List
from src.agents.tools import Tool


class CalculatorTool(Tool):
    """计算器工具"""
    
    def __init__(self):
        super().__init__(
            name="calculator",
            description="执行数学计算，支持基本运算、三角函数、对数等",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "数学表达式，如 '2 + 3 * 4' 或 'sin(pi/2)'"
                    },
                    "precision": {
                        "type": "integer",
                        "description": "结果精度（小数位数），默认6位",
                        "default": 6
                    }
                },
                "required": ["expression"]
            }
        )
        self.supported_operations = {
            'basic': ['+', '-', '*', '/', '^', '%'],
            'functions': ['sin', 'cos', 'tan', 'log', 'ln', 'sqrt', 'abs'],
            'constants': ['pi', 'e']
        }
    
    def execute(self, expression: str, precision: int = 6) -> Dict[str, Any]:
        """执行数学计算"""
        
        try:
            # 预处理表达式
            processed_expr = self._preprocess_expression(expression)
            
            # 安全评估
            result = self._safe_eval(processed_expr)
            
            # 格式化结果
            if isinstance(result, (int, float)):
                # 处理特殊值
                if math.isinf(result):
                    formatted_result = "∞" if result > 0 else "-∞"
                elif math.isnan(result):
                    formatted_result = "NaN"
                else:
                    # 四舍五入到指定精度
                    formatted_result = round(result, precision)
                    
                    # 如果是整数，去掉小数部分
                    if formatted_result == int(formatted_result):
                        formatted_result = int(formatted_result)
            else:
                formatted_result = result
            
            return {
                "success": True,
                "result": formatted_result,
                "expression": expression,
                "precision": precision
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"计算错误: {str(e)}",
                "expression": expression
            }
    
    def _preprocess_expression(self, expression: str) -> str:
        """预处理数学表达式"""
        
        # 移除空格
        expr = expression.replace(' ', '')
        
        # 替换常用符号
        expr = expr.replace('×', '*').replace('÷', '/')
        expr = expr.replace('**', '^')  # Python的幂运算符号
        
        # 处理常量
        expr = expr.replace('π', 'math.pi').replace('pi', 'math.pi')
        expr = expr.replace('e', 'math.e')
        
        # 处理函数调用
        function_mappings = {
            'sin': 'math.sin',
            'cos': 'math.cos', 
            'tan': 'math.tan',
            'log': 'math.log10',
            'ln': 'math.log',
            'sqrt': 'math.sqrt',
            'abs': 'abs'
        }
        
        for func_name, math_func in function_mappings.items():
            # 匹配函数调用 pattern: func_name(number) or func_name (number)
            pattern = rf'{func_name}\s*\('
            expr = re.sub(pattern, f'{math_func}(', expr)
        
        # 处理幂运算（将^转换为**）
        expr = expr.replace('^', '**')
        
        return expr
    
    def _safe_eval(self, expression: str) -> float:
        """安全评估数学表达式"""
        
        # 允许的数学函数和常量
        allowed_names = {
            'math': math,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log10,
            'ln': math.log,
            'sqrt': math.sqrt,
            'abs': abs,
            'pi': math.pi,
            'e': math.e
        }
        
        # 编译表达式
        code = compile(expression, '<string>', 'eval')
        
        # 检查允许的名称
        for name in code.co_names:
            if name not in allowed_names:
                raise ValueError(f"不允许的操作: {name}")
        
        # 执行计算
        result = eval(code, {"__builtins__": {}}, allowed_names)
        
        # 处理特殊值
        if math.isinf(result):
            raise ValueError("结果超出范围")
        if math.isnan(result):
            raise ValueError("无效的计算结果")
        
        return float(result)
    
    def calculate_batch(self, expressions: List[str], precision: int = 6) -> Dict[str, Any]:
        """批量计算多个表达式"""
        
        results = {}
        successful = 0
        failed = 0
        
        for i, expr in enumerate(expressions):
            try:
                result = self.execute(expr, precision)
                results[f"expression_{i}"] = result
                if result["success"]:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                results[f"expression_{i}"] = {
                    "success": False,
                    "error": str(e),
                    "expression": expr
                }
                failed += 1
        
        return {
            'results': results,
            'summary': {
                'total': len(expressions),
                'successful': successful,
                'failed': failed,
                'success_rate': successful / len(expressions) if expressions else 0
            }
        }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """获取计算器能力信息"""
        
        return {
            'supported_operations': self.supported_operations,
            'examples': [
                '2 + 3 * 4',
                'sin(30)',
                'log(100)',
                'sqrt(16)',
                '2^8'
            ],
            'precision': '浮点数精度',
            'limits': '受Python数学库限制'
        }


class ScientificCalculatorTool(CalculatorTool):
    """科学计算器工具 - 扩展功能"""
    
    def __init__(self):
        super().__init__()
        self.name = "scientific_calculator"
        self.description = "科学计算器，支持统计、矩阵、单位转换等高级功能"
        
        # 扩展支持的函数
        self.supported_operations['advanced_functions'] = [
            'factorial', 'gcd', 'lcm', 'degrees', 'radians',
            'asin', 'acos', 'atan', 'sinh', 'cosh', 'tanh'
        ]
    
    def execute(self, expression: str, precision: int = 6) -> Dict[str, Any]:
        """执行科学计算"""
        
        # 先尝试基本计算
        try:
            return super().execute(expression, precision)
        except:
            # 如果基本计算失败，尝试高级功能
            pass
        
        # 处理高级表达式
        try:
            # 扩展函数映射
            advanced_mappings = {
                'factorial': 'math.factorial',
                'gcd': 'math.gcd',
                'lcm': 'math.lcm',
                'degrees': 'math.degrees',
                'radians': 'math.radians',
                'asin': 'math.asin',
                'acos': 'math.acos',
                'atan': 'math.atan',
                'sinh': 'math.sinh',
                'cosh': 'math.cosh',
                'tanh': 'math.tanh'
            }
            
            # 预处理表达式
            expr = expression.replace(' ', '')
            for func_name, math_func in advanced_mappings.items():
                pattern = rf'{func_name}\s*\('
                expr = re.sub(pattern, f'{math_func}(', expr)
            
            # 安全评估
            allowed_names = {
                'math': math,
                **{k: getattr(math, k.split('.')[-1]) for k in advanced_mappings.values()}
            }
            
            code = compile(expr, '<string>', 'eval')
            for name in code.co_names:
                if name not in allowed_names:
                    raise ValueError(f"不允许的操作: {name}")
            
            result = eval(code, {"__builtins__": {}}, allowed_names)
            
            # 格式化结果
            if isinstance(result, (int, float)):
                # 处理特殊值
                if math.isinf(result):
                    formatted_result = "∞" if result > 0 else "-∞"
                elif math.isnan(result):
                    formatted_result = "NaN"
                else:
                    # 四舍五入到指定精度
                    formatted_result = round(result, precision)
                    
                    # 如果是整数，去掉小数部分
                    if formatted_result == int(formatted_result):
                        formatted_result = int(formatted_result)
            else:
                formatted_result = result
            
            return {
                "success": True,
                "result": formatted_result,
                "expression": expression,
                "precision": precision
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"科学计算错误: {str(e)}",
                "expression": expression
            }
    
    def statistical_calculation(self, data: List[float], operation: str, precision: int = 6) -> Dict[str, Any]:
        """统计计算"""
        
        try:
            if not data:
                raise ValueError("数据列表不能为空")
            
            operation = operation.lower()
            
            if operation == 'mean':
                result = sum(data) / len(data)
            elif operation == 'median':
                sorted_data = sorted(data)
                n = len(sorted_data)
                if n % 2 == 1:
                    result = sorted_data[n // 2]
                else:
                    result = (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2
            elif operation == 'std':
                mean = sum(data) / len(data)
                variance = sum((x - mean) ** 2 for x in data) / len(data)
                result = math.sqrt(variance)
            elif operation == 'variance':
                mean = sum(data) / len(data)
                result = sum((x - mean) ** 2 for x in data) / len(data)
            elif operation == 'min':
                result = min(data)
            elif operation == 'max':
                result = max(data)
            elif operation == 'sum':
                result = sum(data)
            else:
                raise ValueError(f"不支持的统计操作: {operation}")
            
            # 格式化结果
            formatted_result = round(result, precision)
            if formatted_result == int(formatted_result):
                formatted_result = int(formatted_result)
            
            return {
                "success": True,
                "result": formatted_result,
                "operation": operation,
                "data_size": len(data),
                "precision": precision
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"统计计算错误: {str(e)}",
                "operation": operation,
                "data_size": len(data) if data else 0
            }
    
    def unit_conversion(self, value: float, from_unit: str, to_unit: str, precision: int = 6) -> Dict[str, Any]:
        """单位转换"""
        
        conversion_factors = {
            # 长度
            'm_to_km': 0.001,
            'km_to_m': 1000,
            'm_to_cm': 100,
            'cm_to_m': 0.01,
            'inch_to_cm': 2.54,
            'cm_to_inch': 0.393701,
            
            # 重量
            'kg_to_g': 1000,
            'g_to_kg': 0.001,
            'kg_to_lb': 2.20462,
            'lb_to_kg': 0.453592,
            
            # 温度（需要特殊处理）
            'c_to_f': lambda c: c * 9/5 + 32,
            'f_to_c': lambda f: (f - 32) * 5/9,
            'c_to_k': lambda c: c + 273.15,
            'k_to_c': lambda k: k - 273.15
        }
        
        conversion_key = f"{from_unit}_to_{to_unit}"
        
        try:
            if conversion_key in conversion_factors:
                factor = conversion_factors[conversion_key]
                
                if callable(factor):
                    result = factor(value)
                else:
                    result = value * factor
                
                # 格式化结果
                formatted_result = round(result, precision)
                if formatted_result == int(formatted_result):
                    formatted_result = int(formatted_result)
                
                return {
                    "success": True,
                    "result": formatted_result,
                    "original_value": value,
                    "from_unit": from_unit,
                    "to_unit": to_unit,
                    "precision": precision
                }
            else:
                raise ValueError(f"不支持的单位转换: {from_unit} -> {to_unit}")
                
        except Exception as e:
            return {
                "success": False,
                "error": f"单位转换错误: {str(e)}",
                "original_value": value,
                "from_unit": from_unit,
                "to_unit": to_unit
            }