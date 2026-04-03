# Summary Bot

`summary_bot` 现在已经扩成跨设备方案：

- `collector-android/` 作为 Android 主采集端
- `app/` 里的 FastAPI 服务作为 Summary Server
- `/mobile` 作为手机 PWA 查看端

## 功能

- 只处理文本消息
- 规则引擎 + LLM 混合分类
- 高优先级消息实时提醒
- 每小时生成一份保研导向摘要
- OpenAI 兼容 API Client
- SQLite 持久化消息、分析、提醒、摘要
- FastAPI 接口接收 Android collector 上报、查看消息和报告
- 手机 PWA 页面：最新摘要、告警、待办、搜索、设备状态
- Android collector skeleton：通知监听、群白名单、队列、上报
- Mock / 文件回放 collector，便于本地开发
- Linux QQ 通知 collector 仍保留，适合作为桌面补充源

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
  collector-android/
  scripts/
  tests/
```

## 核心链路

```text
android collector -> /api/v1/collector/events -> normalizer -> dedup -> rule_engine
                                                                -> classifier -> alerting -> storage
storage -> clusterer -> summarizer -> hourly_reports -> /api/v1/mobile/* -> /mobile PWA
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

如果你准备部署“服务器模式”，建议 `.env` 至少设置成：

```bash
MESSAGE_SOURCE=none
COLLECTOR_SHARED_TOKEN=change-me
ENABLE_SCHEDULER=true
```

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
- `POST /api/v1/collector/events`
- `POST /api/v1/collector/heartbeat`
- `GET /api/v1/mobile/feed`
- `GET /api/v1/mobile/alerts`
- `GET /api/v1/mobile/reports`
- `GET /api/v1/mobile/search`
- `GET /mobile`

## Android 主采集端

Android 采集端在 [collector-android/README.md](/home/zhouxiaohao/code_search/projects/summary_bot/collector-android/README.md)。

它的职责是：

1. 读取 QQ 通知
2. 按群白名单过滤
3. 本地排队缓存
4. 上传到服务器

服务器上需要配置：

```bash
COLLECTOR_SHARED_TOKEN=your-secret-token
```

Android 应用里需要填写：

- `Server URL`
- `Collector Token`
- `Allowed Groups`
- `Group Filter Mode`

## 手机 PWA

启动服务器后，手机浏览器直接打开：

```text
https://your-server/mobile
```

PWA 页面包含：

- 最新小时摘要
- 高优先级告警
- 今日待办
- 设备在线状态
- 消息搜索

如果浏览器支持，可以直接“添加到主屏幕”。

## 桌面补充 collector

项目仍然保留一个 Linux 侧真实 collector：

- `QQNotificationCollector`

这个 collector 的工作方式是：

1. 你先在本机手动登录个人 QQ
2. 开启 QQ 的桌面消息通知
3. collector 监听 Linux 桌面通知总线
4. 只采集你指定的一个或多个群聊

它适合放在你电脑上作为 Android 采集的补充源，不建议作为第一优先主采集端。

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

- 优先走 tool calling 做结构化输出
- tool calling 不支持时再尝试 JSON 输出模式
- 带重试
- 顶层 schema 校验

## 测试

```bash
cd /home/zhouxiaohao/code_search/projects/summary_bot
pytest
```

## 当前限制

- Android collector 依赖 QQ 真的发出系统通知
- Android 项目目前是 skeleton，建议用 Android Studio 打开并在真机上调试
- PWA 已可用，但 Web Push 还没有接
- PDF 导出还没做，当前建议用浏览器打印保存
