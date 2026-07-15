import React, { useEffect, useState } from 'react';
import { Table, Button, Tag, Switch, Space, Modal, Form, Input, Select, message, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { useSources, useSaveSources } from '../../hooks/useConfig';
import { SOURCE_TYPES } from '../../utils/constants';
import type { SourceConfig } from '../../api/types';

const SourceSettings: React.FC = () => {
  const { data, isLoading } = useSources();
  const saveMutation = useSaveSources();
  const [sources, setSources] = useState<SourceConfig[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    if (data?.sources) setSources(data.sources);
  }, [data]);

  const handleToggle = (index: number, enabled: boolean) => {
    setSources((prev) => prev.map((s, i) => (i === index ? { ...s, enabled } : s)));
  };

  const handleAdd = async () => {
    try {
      const values = await form.validateFields();
      setSources((prev) => [...prev, { ...values, enabled: true }]);
      form.resetFields();
      setModalOpen(false);
    } catch { /* ignore */ }
  };

  const handleDelete = (index: number) => {
    setSources((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    try {
      await saveMutation.mutateAsync(sources);
      message.success('内容源已保存');
    } catch {
      message.error('保存失败');
    }
  };

  const columns: ColumnsType<SourceConfig> = [
    { title: '名称', dataIndex: 'name', width: 200 },
    {
      title: '类型',
      dataIndex: 'type',
      width: 120,
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    { title: '标识', dataIndex: 'identifier', ellipsis: true },
    {
      title: '启用',
      width: 80,
      render: (_: unknown, __: SourceConfig, index: number) => (
        <Switch
          size="small"
          checked={sources[index]?.enabled}
          onChange={(checked) => handleToggle(index, checked)}
        />
      ),
    },
    {
      title: '操作',
      width: 60,
      render: (_: unknown, __: SourceConfig, index: number) => (
        <Popconfirm title="确定删除？" onConfirm={() => handleDelete(index)}>
          <Button type="text" danger size="small" icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          添加内容源
        </Button>
        <Button type="primary" onClick={handleSave} loading={saveMutation.isPending}>
          保存
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={sources}
        rowKey={(r) => `${r.type}-${r.name}`}
        size="small"
        loading={isLoading}
        pagination={false}
      />

      <Modal
        title="添加内容源"
        open={modalOpen}
        onOk={handleAdd}
        onCancel={() => setModalOpen(false)}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="type" label="类型" rules={[{ required: true }]}>
            <Select options={SOURCE_TYPES} />
          </Form.Item>
          <Form.Item name="identifier" label="标识" rules={[{ required: true }]}>
            <Input placeholder="URL / 文件路径 / CLI 命令" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SourceSettings;
