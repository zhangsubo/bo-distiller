#!/usr/bin/env python3
"""
模块依赖分析工具
分析 bo-distiller 项目的模块依赖关系
"""

import ast
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

class DependencyAnalyzer:
    """依赖关系分析器"""

    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.dependencies = defaultdict(set)  # 模块 -> 依赖的模块集合
        self.reverse_deps = defaultdict(set)  # 模块 -> 被哪些模块依赖
        self.all_modules = set()

    def analyze(self):
        """分析所有 Python 文件的依赖关系"""
        py_files = list(self.root_dir.glob("**/*.py"))

        # 排除虚拟环境和构建目录
        py_files = [f for f in py_files if not any(
            part in f.parts for part in ['venv', 'env', '__pycache__', 'build', 'dist', '.venv']
        )]

        for file_path in py_files:
            module_name = self._get_module_name(file_path)
            if module_name:
                self.all_modules.add(module_name)
                imports = self._extract_imports(file_path)
                self.dependencies[module_name] = imports

                # 构建反向依赖
                for imp in imports:
                    self.reverse_deps[imp].add(module_name)

    def _get_module_name(self, file_path: Path) -> str:
        """将文件路径转换为模块名"""
        try:
            rel_path = file_path.relative_to(self.root_dir)
            parts = list(rel_path.parts)

            # 移除 .py 后缀
            if parts[-1].endswith('.py'):
                parts[-1] = parts[-1][:-3]

            # __init__.py 对应目录本身
            if parts[-1] == '__init__':
                parts = parts[:-1]

            return '.'.join(parts) if parts else ''
        except ValueError:
            return ''

    def _extract_imports(self, file_path: Path) -> Set[str]:
        """提取文件中的导入语句"""
        imports = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imp = self._normalize_import(alias.name)
                        if imp:
                            imports.add(imp)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imp = self._normalize_import(node.module)
                        if imp:
                            imports.add(imp)

        except Exception as e:
            print(f"解析失败 {file_path}: {e}")

        return imports

    def _normalize_import(self, import_name: str) -> str:
        """规范化导入名称，只保留项目内的导入"""
        # 只保留 src, cli, tests 开头的导入
        if import_name.startswith(('src.', 'cli.', 'tests.')):
            # 提取顶层模块
            parts = import_name.split('.')
            if len(parts) >= 2:
                return '.'.join(parts[:2])  # src.models, src.config 等
            return parts[0]

        # 根目录脚本（distill, web_ui 等）
        if '.' not in import_name and import_name in [
            'distill', 'web_ui', 'analyze_content', 'classify_upgrade', 'analyze_cubox_content'
        ]:
            return import_name

        return ''

    def find_cycles(self) -> List[List[str]]:
        """检测循环依赖"""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(module: str):
            if module in rec_stack:
                # 找到环
                cycle_start = path.index(module)
                cycle = path[cycle_start:] + [module]
                cycles.append(cycle)
                return

            if module in visited:
                return

            visited.add(module)
            rec_stack.add(module)
            path.append(module)

            for dep in self.dependencies.get(module, set()):
                if dep in self.all_modules:
                    dfs(dep)

            path.pop()
            rec_stack.remove(module)

        for module in self.all_modules:
            if module not in visited:
                dfs(module)

        return cycles

    def find_unused_modules(self) -> Set[str]:
        """查找未被使用的模块"""
        # 根目录入口脚本不算未使用
        entry_points = {'distill', 'web_ui', 'analyze_content', 'classify_upgrade'}

        unused = set()
        for module in self.all_modules:
            # 跳过入口点
            if module in entry_points or module.startswith('tests.'):
                continue

            # 如果没有被其他模块导入，且不是入口点，则为未使用
            if not self.reverse_deps.get(module):
                unused.add(module)

        return unused

    def get_module_stats(self) -> Dict[str, Dict]:
        """获取模块统计信息"""
        stats = {}

        for module in sorted(self.all_modules):
            deps = self.dependencies.get(module, set())
            used_by = self.reverse_deps.get(module, set())

            stats[module] = {
                'dependencies': len(deps & self.all_modules),
                'used_by': len(used_by),
                'deps_list': sorted(deps & self.all_modules),
                'used_by_list': sorted(used_by)
            }

        return stats


def print_report(analyzer: DependencyAnalyzer):
    """打印分析报告"""

    print("=" * 80)
    print("Bo-Distiller 模块依赖分析报告")
    print("=" * 80)
    print()

    # 1. 模块概览
    print("## 1. 模块概览")
    print()

    modules_by_category = defaultdict(list)
    for module in sorted(analyzer.all_modules):
        category = module.split('.')[0] if '.' in module else '根目录'
        modules_by_category[category].append(module)

    for category, modules in sorted(modules_by_category.items()):
        print(f"### {category} ({len(modules)} 个模块)")
        for mod in modules:
            print(f"  - {mod}")
        print()

    # 2. 核心依赖关系
    print("## 2. 核心模块依赖关系")
    print()

    core_modules = [
        'src.models', 'src.config', 'src.storage', 'src.cache',
        'src.llm_client', 'src.synthesizer',
        'src.processors', 'src.adapters'
    ]

    stats = analyzer.get_module_stats()

    for module in core_modules:
        if module in stats:
            info = stats[module]
            print(f"### {module}")
            print(f"  依赖: {info['dependencies']} 个模块")
            if info['deps_list']:
                for dep in info['deps_list']:
                    print(f"    → {dep}")
            print(f"  被依赖: {info['used_by']} 个模块")
            if info['used_by_list'][:5]:  # 只显示前5个
                for used in info['used_by_list'][:5]:
                    print(f"    ← {used}")
                if len(info['used_by_list']) > 5:
                    print(f"    ... 还有 {len(info['used_by_list']) - 5} 个")
            print()

    # 3. 循环依赖检测
    print("## 3. 循环依赖检测")
    print()

    cycles = analyzer.find_cycles()
    if cycles:
        print(f"⚠️  发现 {len(cycles)} 个循环依赖:")
        for i, cycle in enumerate(cycles, 1):
            print(f"\n  循环 {i}:")
            print("    " + " → ".join(cycle))
    else:
        print("✅ 未发现循环依赖")
    print()

    # 4. 未使用的模块
    print("## 4. 未使用的模块")
    print()

    unused = analyzer.find_unused_modules()
    if unused:
        print(f"发现 {len(unused)} 个未被导入的模块:")
        for mod in sorted(unused):
            print(f"  - {mod}")
    else:
        print("✅ 所有模块都被使用")
    print()

    # 5. 依赖层级分析
    print("## 5. 依赖层级分析")
    print()

    # 基础层（不依赖其他项目模块）
    base_layer = {m for m in analyzer.all_modules
                  if not (analyzer.dependencies.get(m, set()) & analyzer.all_modules)}

    # 高耦合模块（依赖 > 5 个）
    highly_coupled = {m for m, info in stats.items() if info['dependencies'] > 5}

    # 核心模块（被依赖 > 5 次）
    core_used = {m for m, info in stats.items() if info['used_by'] > 5}

    print(f"### 基础层模块 ({len(base_layer)} 个)")
    print("  （不依赖其他项目模块）")
    for mod in sorted(base_layer):
        print(f"  - {mod}")
    print()

    print(f"### 高耦合模块 ({len(highly_coupled)} 个)")
    print("  （依赖 > 5 个其他模块）")
    for mod in sorted(highly_coupled):
        print(f"  - {mod}: 依赖 {stats[mod]['dependencies']} 个")
    print()

    print(f"### 核心模块 ({len(core_used)} 个)")
    print("  （被 > 5 个模块依赖）")
    for mod in sorted(core_used):
        print(f"  - {mod}: 被 {stats[mod]['used_by']} 个模块使用")
    print()

    # 6. 优化建议
    print("## 6. 优化建议")
    print()

    suggestions = []

    if cycles:
        suggestions.append("⚠️  **消除循环依赖**: 重构循环引用的模块，考虑使用依赖注入或接口抽象")

    if unused:
        suggestions.append(f"🧹 **清理未使用模块**: 移除或归档 {len(unused)} 个未被导入的模块")

    if highly_coupled:
        suggestions.append(f"📦 **降低耦合度**: {len(highly_coupled)} 个模块依赖过多，考虑拆分或使用 facade 模式")

    # 检查 adapters 和 processors 的依赖
    adapter_deps = [m for m in analyzer.all_modules if m.startswith('src.adapters.')]
    processor_deps = [m for m in analyzer.all_modules if m.startswith('src.processors.')]

    if adapter_deps:
        # 检查 adapter 是否相互依赖
        adapter_cross_deps = []
        for adapter in adapter_deps:
            deps = analyzer.dependencies.get(adapter, set())
            cross = deps & set(adapter_deps)
            if cross:
                adapter_cross_deps.append((adapter, cross))

        if adapter_cross_deps:
            suggestions.append("🔌 **Adapter 独立性**: 部分 adapter 相互依赖，应保持独立")

    if not suggestions:
        suggestions.append("✅ **依赖结构良好**: 当前依赖关系清晰，无明显问题")

    for i, suggestion in enumerate(suggestions, 1):
        print(f"{i}. {suggestion}")
    print()

    print("=" * 80)


if __name__ == "__main__":
    analyzer = DependencyAnalyzer("/Users/zhangsubo/Code/bo-distiller")
    analyzer.analyze()
    print_report(analyzer)
