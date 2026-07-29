"""
pytest 配置文件
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# pytest 配置
def pytest_configure(config):
    """pytest 配置钩子"""
    config.addinivalue_line(
        "markers", "integration: 标记集成测试（需要外部依赖）"
    )
    config.addinivalue_line(
        "markers", "slow: 标记慢速测试"
    )
