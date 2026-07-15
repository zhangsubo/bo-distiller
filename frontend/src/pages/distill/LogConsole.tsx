import React, { useEffect, useRef, useState } from 'react';
import { Card, Empty } from 'antd';
import { useDistillStatus } from '../../hooks/useDistillProgress';

const LogConsole: React.FC = () => {
  const { data } = useDistillStatus();
  const running = data?.data?.running ?? false;
  const [logs, setLogs] = useState<string[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (running) {
      setLogs([]);
      const es = new EventSource('/api/distill/stream');
      eventSourceRef.current = es;

      es.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.log) {
            setLogs((prev) => [...prev.slice(-200), payload.log]);
          }
          if (payload.done) {
            es.close();
          }
        } catch { /* ignore */ }
      };

      es.onerror = () => {
        es.close();
      };

      return () => es.close();
    } else {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    }
  }, [running]);

  // 自动滚动到底部
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <Card title="实时日志" size="small">
      {logs.length === 0 && !running ? (
        <Empty description="暂无日志" />
      ) : (
        <div
          ref={containerRef}
          style={{
            background: '#1e1e1e',
            color: '#d4d4d4',
            padding: 12,
            borderRadius: 6,
            height: 300,
            overflow: 'auto',
            fontFamily: 'Menlo, Monaco, "Courier New", monospace',
            fontSize: 12,
            lineHeight: 1.6,
          }}
        >
          {logs.map((line, i) => (
            <div key={i}>{line}</div>
          ))}
          {running && <div style={{ color: '#4fc1ff' }}>● 运行中...</div>}
        </div>
      )}
    </Card>
  );
};

export default LogConsole;
