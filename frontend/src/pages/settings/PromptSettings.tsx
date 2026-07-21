import React, { useEffect, useState } from 'react';
import { Card, Input, Button, Alert, Form, message, Spin } from 'antd';
import { usePrompts, useSavePrompts } from '../../hooks/useSystemSettings';
import type { PromptTemplate, PromptsConfig } from '../../api/types';

const { TextArea } = Input;

function isTemplate(value: unknown): value is PromptTemplate {
  return (
    typeof value === 'object' &&
    value !== null &&
    ('system' in value || 'user_template' in value)
  );
}

const PromptSettings: React.FC = () => {
  const { data, isLoading } = usePrompts();
  const saveMutation = useSavePrompts();
  const [templates, setTemplates] = useState<Record<string, PromptTemplate>>({});

  useEffect(() => {
    if (data?.prompts) {
      const result: Record<string, PromptTemplate> = {};
      Object.entries(data.prompts).forEach(([key, value]) => {
        if (key !== 'settings' && isTemplate(value)) {
          result[key] = { ...value };
        }
      });
      setTemplates(result);
    }
  }, [data]);

  const handleChange = (key: string, field: 'system' | 'user_template', value: string) => {
    setTemplates((prev) => ({
      ...prev,
      [key]: { ...prev[key], [field]: value },
    }));
  };

  const handleSave = async () => {
    try {
      // 保留 settings 等非模板字段，整体写回
      const merged: PromptsConfig = { ...(data?.prompts || {}), ...templates };
      await saveMutation.mutateAsync(merged);
      message.success('提示词已保存');
    } catch {
      message.error('保存失败');
    }
  };

  if (isLoading) return <Spin />;

  const keys = Object.keys(templates);

  return (
    <div>
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message="提示词模板说明"
        description="模板中的占位符（如 synthesis 模板里的 {batch_count}）由程序运行时替换，请勿删除或改名。"
      />

      {keys.length === 0 && <div>暂无提示词配置</div>}

      {keys.map((key) => {
        const tpl = templates[key];
        return (
          <Card key={key} title={key} size="small" style={{ marginBottom: 16 }}>
            <Form layout="vertical">
              <Form.Item label="system" style={{ marginBottom: 12 }}>
                <TextArea
                  autoSize={{ minRows: 4 }}
                  value={tpl.system ?? ''}
                  onChange={(e) => handleChange(key, 'system', e.target.value)}
                />
              </Form.Item>
              {tpl.user_template !== undefined && (
                <Form.Item label="user_template" style={{ marginBottom: 0 }}>
                  <TextArea
                    autoSize={{ minRows: 4 }}
                    value={tpl.user_template}
                    onChange={(e) => handleChange(key, 'user_template', e.target.value)}
                  />
                </Form.Item>
              )}
            </Form>
          </Card>
        );
      })}

      <Button type="primary" onClick={handleSave} loading={saveMutation.isPending}>
        保存提示词
      </Button>
    </div>
  );
};

export default PromptSettings;
