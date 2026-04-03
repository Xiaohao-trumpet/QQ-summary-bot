# Android Collector

这个子项目是 `summary_bot` 的 Android 主采集端。它不负责总结，只负责：

- 监听 QQ 通知
- 按群白名单过滤
- 本地缓存待上传事件
- 上传到服务器 `/api/v1/collector/events`

## 使用步骤

1. 用 Android Studio 打开 `collector-android`
2. 修改服务器地址和 collector token
3. 安装到 Android 手机
4. 给应用授予通知读取权限
5. 保证手机 QQ 正常登录并开启群通知

## 关键前提

- 只适合 Android
- 依赖 QQ 真的发出系统通知
- 群如果被完全静音到不弹通知，就采不到

## 服务器配置

服务器 `.env` 里需要至少设置：

```bash
COLLECTOR_SHARED_TOKEN=your-secret-token
```

Android 端应用里配置：

- Server URL: `https://your-server`
- Collector Token: `your-secret-token`
- Allowed Groups: 逗号分隔的群名

