# 环境部署说明

这份说明只解决一件事：把 `summary_bot` 的本地 Python 环境装好，确保你后面可以直接跑 demo、API 和测试。

## 1. 进入项目目录

```bash
cd /home/zhouxiaohao/code_search/projects/summary_bot
```

## 2. 创建虚拟环境

推荐用 Python 3.11 到 3.13。

```bash
python -m venv .venv
source .venv/bin/activate
```

如果你用的是 Conda，也可以：

```bash
conda create -n summary_bot python=3.11 -y
conda activate summary_bot
```

## 3. 安装依赖

优先用 `requirements.txt`：

```bash
pip install -r requirements.txt
```

如果你希望以可编辑模式安装项目，也可以：

```bash
pip install -e .[dev]
```

## 4. 配置环境变量

复制模板：

```bash
cp .env.example .env
```

最少只需要检查这几个字段：

```bash
DATABASE_URL=sqlite:///./summary_bot.db
MESSAGE_SOURCE=none
COLLECTOR_SHARED_TOKEN=change-me
ALERT_CHANNELS=console
```

如果你要启用 LLM，再额外填写：

```bash
OPENAI_BASE_URL=...
OPENAI_API_KEY=...
OPENAI_MODEL=...
```

如果不填这三项，系统会自动退回规则引擎和确定性摘要，项目仍然可以运行。

## 5. 验证依赖是否安装成功

你可以先做一个最小检查：

```bash
python -c "import fastapi, httpx, sqlalchemy, pydantic, apscheduler; print('deps ok')"
```

如果输出 `deps ok`，说明核心依赖已经装好。

## 6. 跑 Demo

```bash
python scripts/run_demo.py
```

这会读取 `data/mock_messages.jsonl`，完成：

- 消息回放
- 规则分析
- 提醒生成
- 小时摘要生成

## 6.1 启用真实 QQ collector

如果你要监听本机已登录的 QQ 群消息，请先确认：

- QQ 已登录
- Linux 桌面通知正常
- QQ 对目标群会弹出系统通知

然后在 `.env` 里配置：

```bash
MESSAGE_SOURCE=qq_notification
QQ_ALLOWED_GROUPS=清华软院预推免群,北大信息学院套磁群
QQ_GROUP_FILTER_MODE=exact
```

如果你想先看 collector 能否抓到 QQ 通知，可以运行：

```bash
python scripts/debug_qq_notifications.py
```

这个脚本会持续打印被解析出的群名、发送人和文本内容。

## 7. 启动 API

```bash
uvicorn app.main:app --reload
```

常用接口：

- `GET /health`
- `GET /messages`
- `GET /reports`
- `POST /api/v1/collector/events`
- `GET /api/v1/mobile/feed`
- `GET /mobile`

## 7.1 启动手机 PWA

服务器起来之后，手机浏览器访问：

```text
https://your-server/mobile
```

如果你使用的是本地调试，也可以先在电脑浏览器打开：

```text
http://127.0.0.1:8000/mobile
```

## 7.2 Android Collector

Android 主采集端代码在：

[collector-android/README.md](/home/zhouxiaohao/code_search/projects/summary_bot/collector-android/README.md)

你需要在 Android Studio 中：

1. 打开 `collector-android`
2. 安装到安卓手机
3. 授予通知读取权限
4. 在 App 中填写：
   - Server URL
   - Collector Token
   - Allowed Groups
   - Filter Mode
5. 确保手机 QQ 已登录，且目标群会弹系统通知

## 8. 跑测试

```bash
pytest
```

如果你的环境里 `pytest` 命令找不到，也可以：

```bash
python -m pytest
```

## 9. 常见问题

### 1. 缺少依赖

报错类似：

```text
ModuleNotFoundError: No module named 'fastapi'
```

解决：

```bash
python -m pip install -r requirements.txt
```

如果你的环境里设置了类似下面的代理变量：

```bash
ALL_PROXY=socks5h://127.0.0.1:7890
```

那就必须确保已经安装 `socksio`。当前 `requirements.txt` 已经包含它。

### 2. 使用了系统 Python，但没进虚拟环境

先检查：

```bash
which python
which pip
```

如果不是 `.venv/bin/python` 和 `.venv/bin/pip`，说明你还没激活虚拟环境。

### 3. 没配 LLM

这是允许的。当前项目支持无 LLM 模式，只是摘要会退回规则化输出。

## 10. 建议的安装顺序

最稳妥的一套服务器启动命令是：

```bash
cd /home/zhouxiaohao/code_search/projects/summary_bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
