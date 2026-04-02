# Summary Bot

`summary_bot` 是一个面向保研场景的 QQ 群文本消息监控与摘要 MVP。当前版本专注于把“消息处理链路”跑通，不直接耦合真实 QQ 采集逻辑，而是通过 `collector` 抽象预留接入点。

## 功能

- 只处理文本消息
- 规则引擎 + LLM 混合分类
- 高优先级消息实时提醒
- 每小时生成一份保研导向摘要
- OpenAI 兼容 API Client
- SQLite 持久化消息、分析、提醒、摘要
- FastAPI 接口查看消息和报告
- Mock / 文件回放 collector，便于本地开发
- 基于 Linux 桌面通知的真实 QQ collector，可按群名白名单采集

## 目录

```text
summary_bot/
  app/
    api/
    collector/
    llm/
    pipeline/
    services/
    storage/
  data/
  scripts/
  tests/
```

## 核心链路

```text
collector -> normalizer -> dedup -> rule_engine -> classifier -> alerting
                                                     -> storage
storage -> clusterer -> summarizer -> hourly_reports
```

## 安装

```bash
cd /home/zhouxiaohao/code_search/projects/summary_bot
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

如果你想先按最简单方式装依赖，直接看环境说明：[ENV_SETUP.md](/home/zhouxiaohao/code_search/projects/summary_bot/docs/ENV_SETUP.md)。

## 配置

复制环境变量模板：

```bash
cp .env.example .env
```

如果你要启用真实 LLM，请配置：

```bash
OPENAI_BASE_URL=...
OPENAI_API_KEY=...
OPENAI_MODEL=...
```

不配置也可以运行，系统会退回规则引擎和确定性摘要。

## 运行 Demo

```bash
cd /home/zhouxiaohao/code_search/projects/summary_bot
python scripts/run_demo.py
```

这会：

1. 从 `data/mock_messages.jsonl` 回放消息
2. 写入 SQLite
3. 执行分析与提醒
4. 生成一份小时摘要并打印到终端

## 启动 API

```bash
cd /home/zhouxiaohao/code_search/projects/summary_bot
uvicorn app.main:app --reload
```

接口：

- `GET /health`
- `GET /messages`
- `GET /reports`
- `GET /reports/{report_id}`

## 真实 QQ 接入建议

当前项目已经提供一个真实 collector：

- `QQNotificationCollector`

这个 collector 的工作方式是：

1. 你先在本机手动登录个人 QQ
2. 开启 QQ 的桌面消息通知
3. collector 监听 Linux 桌面通知总线
4. 只采集你指定的一个或多个群聊

它不依赖官方群机器人，也不要求非官方协议登录。代价是它依赖 QQ 通知格式，并且只能抓到“系统发出的新消息通知”。

启用方式：

```bash
MESSAGE_SOURCE=qq_notification
QQ_ALLOWED_GROUPS=清华软院预推免群,北大信息学院套磁群
QQ_GROUP_FILTER_MODE=exact
```

如果你的 QQ 通知 `app_name` 不是默认值，可以调整：

```bash
QQ_NOTIFICATION_APP_NAMES=QQ,linuxqq,com.tencent.qq,com.tencent.mobileqq
```

使用前提：

- QQ 已登录
- 群消息通知未被关闭
- Linux 系统通知正常工作
- 你要监控的群没有被静音到完全不弹通知

## LLM 设计

- `app/llm/client.py` 实现 OpenAI 兼容 `/v1/chat/completions` 调用
- `app/llm/prompts.py` 放置单条分类和小时摘要提示词
- `app/llm/schemas.py` 定义结构化输出 schema

客户端特性：

- 支持 JSON 输出模式
- 不支持时退回文本并提取 JSON
- 带重试
- 顶层 schema 校验

## 测试

```bash
cd /home/zhouxiaohao/code_search/projects/summary_bot
pytest
```

## 后续建议

- 增加真实 QQ collector
- 增加时间解析，把“今晚”“明早”转成绝对时间
- 增加消息发送人画像，区分老师/管理员/群友
- 增加多群事件去重
- 增加 Web 面板或桌面提醒通道
