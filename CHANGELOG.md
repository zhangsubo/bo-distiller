# 变更日志

Bo-Distiller 项目的所有重要变更都记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增
- 新增 `src/orchestrator.py` — 蒸馏业务编排函数
- 新增 `src/utils.py` — 共享工具函数（token 计数、文章格式化、引用替换）
- 新增 `scripts/` 目录 — 独立分析脚本统一存放

### 改进
- 重构 `distill.py` — CLI 定义与业务逻辑分离
- 重构 `storage.py` — 提取 `_upsert_article` 消除 SQL 重复
- 重构 `llm_client.py` — 移除过度设计的 Factory 类，改为模块级单例
- 重构 `synthesizer.py` — 提取共用工具函数到 `utils.py`
- 重构 `cache.py` — 移除 pickle，统一使用 JSON 序列化
- 重构 `web/deps.py` — 移除 `sys.path` hack，统一到 `web/__init__.py`

### 移除
- 移除微信公众号下载工具（两个版本均失效）
  - 删除 `wechat-exporter/`、`src/services/wechat_native/`
  - 删除 `src/services/wechat_downloader.py`、`wechat_queue.py`
  - 删除前端微信相关页面、API、路由
  - 清理所有配置和文档中的微信引用

## [0.2.0] - 2024-07-25

### 新增
- Web UI 集成
- Docker 支持
  - 完整的 Docker 镜像
  - docker-compose 配置
  - 本地配置挂载

### 改进
- 改进 SQLite 数据库结构
- 增强错误处理和日志记录

### 文档
- 新增 Web 集成文档
- 新增 Docker 使用说明

## [0.1.0] - 2024-07-13

### 新增
- 🎯 Cubox 内容智能分析系统
  - 分析 2,697 篇文章
  - 识别 20+ 个主题聚类
  - 检测 103 组重复文章
  - 高频关键词提取
- 智能分类功能
  - 关键词分类方法
  - 向量相似度分类
  - 混合分类策略
- 分类报告生成
  - JSON 格式详细数据
  - Markdown 格式可读报告

### 改进
- 优化文本预处理流程
- 改进 TF-IDF 特征提取
- 增强重复检测算法

### 文档
- 新增分类系统快速开始指南
- 新增完整分析报告
- 新增项目总结文档

## [0.0.1] - 2024-07-10

### 新增
- ✅ 核心框架实现
  - 数据模型（Article, SourceInfo, SystemConfig）
  - 配置管理（YAML + 环境变量）
  - LLM 客户端（统一接口，支持多提供商）
  - 缓存管理（多层缓存，断点续传）
  - 内容清洗（HTML 清洗、噪音去除）
  - 知识合成（两阶段合成）
- CLI 命令
  - `run` - 运行蒸馏流程
  - `status` - 查看项目状态
  - `serve` - 启动 Web UI
- LLM 支持
  - DeepSeek
  - Mimo (小米)
  - MiniMax
  - Kimi
- 基础 Web UI
  - FastAPI 后端
  - React 前端
  - 实时进度显示

### 文档
- 完整设计文档（Reference_myself/）
  - 架构设计
  - 核心机制设计
  - 技术选型
  - 实现路线图
- 项目 README
- 快速开始指南
- API 文档

## [计划中]

### v0.3.0 - 测试完善
- [ ] 补充核心模块单元测试（目标覆盖率 60%+）
- [ ] 添加集成测试
- [ ] 配置 CI/CD
- [ ] 性能优化

### v0.4.0 - CLI 统一
- [ ] 统一 CLI 入口
- [ ] 改进内容源管理
- [ ] 增强错误提示

### v0.5.0 - 多源聚合
- [ ] RSS 源适配器
- [ ] 本地 Markdown 文件支持
- [ ] 书签导入功能
- [ ] 多源内容融合

### v1.0.0 - 正式版
- [ ] 知识图谱可视化
- [ ] 智能主题发现
- [ ] 增量更新优化
- [ ] 完整用户文档
- [ ] 性能基准测试

---

## 版本说明

- **主版本号**：重大架构变更或不兼容的 API 修改
- **次版本号**：向后兼容的功能新增
- **修订号**：向后兼容的问题修复

## 链接

- [项目仓库](https://github.com/yourusername/bo-distiller)
- [问题追踪](https://github.com/yourusername/bo-distiller/issues)
- [发布记录](https://github.com/yourusername/bo-distiller/releases)
