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
MESSAGE_SOURCE=file
MESSAGE_SOURCE_PATH=./data/mock_messages.jsonl
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

## 7. 启动 API

```bash
uvicorn app.main:app --reload
```

常用接口：

- `GET /health`
- `GET /messages`
- `GET /reports`

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
pip install -r requirements.txt
```

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

最稳妥的一套命令是：

```bash
cd /home/zhouxiaohao/code_search/projects/summary_bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/run_demo.py
```

