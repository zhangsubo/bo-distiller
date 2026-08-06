"""回归测试：logs 超过 1000 条截断后，log_seq 仍能正确标识新增日志。

SSE 生成器曾用 len(logs) 判断新日志，截断后 len 停在 1000，流永久冻结。
"""

from src.web.tasks import DistillTask


def test_log_seq_monotonic_after_trimming():
    task = DistillTask(provider="test")
    for i in range(1200):
        task.add_log(f"log {i}")

    assert len(task.logs) == 1000  # 列表被截断
    assert task.log_seq == 1200  # 序号持续增长

    # 模拟 SSE 生成器：从 seq=1190 开始取新增
    last_seq = 1190
    new_count = task.log_seq - last_seq
    new_logs = task.logs[-new_count:] if new_count < len(task.logs) else task.logs
    assert new_logs[-1].endswith("log 1199")
    assert len(new_logs) == 10
