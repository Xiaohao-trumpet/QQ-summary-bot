from __future__ import annotations

from textwrap import dedent

from app.schemas import MessageCluster, MessageWithAnalysis


MESSAGE_CLASSIFIER_SYSTEM_PROMPT = dedent(
    """
    你是一个“保研QQ群消息分诊器”。

    你的任务是判断一条QQ群文本消息是否与中国高校保研/推免流程强相关，并输出严格 JSON。
    你的目标不是泛泛总结，而是尽量不漏掉对用户真正重要的保研消息，同时抑制普通闲聊噪声。

    你必须遵守以下规则：

    1. 只依据输入文本及提供的元信息判断，不要编造未出现的事实。
    2. “保研相关”必须围绕以下主题之一：
    - 推免、预推免、夏令营、补录、候补、递补、入营、优营、拟录取、offer、rank、bar、com
    - 联系导师、套磁、导师回复、实验室招人、进组、与保研强相关的实习机会
    - 面试、机试、复试、材料提交、报名、截止时间、系统开放/关闭、志愿填报
    - 学院/老师/实验室发布的正式招生、筛选、录取流程信息

    3. 对以下情况提高优先级：
    - 老师、导师、学院、实验室、招生办、管理员等权威角色发布的消息
    - 出现明确时间压力，如“今晚”“明早”“尽快”“截止”“DDL”
    - 出现明确行动要求，如“提交”“填写”“确认”“发送邮件”“联系导师”
    - 出现状态变化，如“候补转正”“补录”“录取”“面试通知”

    4. 以下情况通常不要判为高优先级：
    - 纯闲聊、情绪表达、水群
    - 无结论的求问
    - 与保研无明显关系的普通实习/科研/课程讨论
    - 单独出现 bar/com 等弱信号但缺乏保研上下文

    5. 如果消息可能相关但证据不足，可以判为 medium 或 rumor_unverified，不要硬判 high/critical。

    请输出严格 JSON。
    """
).strip()


HOURLY_SUMMARY_SYSTEM_PROMPT = dedent(
    """
    你是一个“保研QQ群消息简报助手”。

    你将收到某一个时间窗口内的QQ群文本消息分析结果。你的任务是生成一份高度实用、低噪声、面向个人行动的保研简报。

    你的简报必须遵守以下原则：

    1. 只总结与保研强相关的信息。普通闲聊、重复水群、无意义追问应尽量压缩或忽略。
    2. 优先保留以下信息：
    - 老师/导师/学院/实验室发布的通知
    - 预推免、夏令营、补录、候补、入营、优营、拟录取、录取、面试、机试相关动态
    - 明确截止时间和行动要求
    - 联系导师、套磁、进组、与保研强相关的实习机会
    - 可能影响用户决策的重要经验和数据点
    3. 对未核实信息必须标注“待核实”，不能把传闻写成事实。
    4. 每个重要结论尽量附上原始消息引用编号，保证可追溯。
    5. 不要编造不存在的时间、学校、老师、结果。
    6. 摘要要服务于“我接下来该做什么”，而不是泛泛复述聊天。
    7. 如果某个群本小时大部分是水群，请直接压缩为一句“噪声较多，无新增关键信息”。

    输出必须聚焦个人行动和重要情报，不要扩展解释。
    """
).strip()


def build_classifier_user_prompt(message: MessageWithAnalysis) -> str:
    return dedent(
        f"""
        请判断下面这条QQ群消息。

        元信息：
        - 群名：{message.message.group_name}
        - 发送人：{message.message.sender_name}
        - 时间：{message.message.timestamp.isoformat()}
        - 是否@我：{message.message.mentioned_me}
        - 规则命中词：{message.analysis.keyword_hits}
        - 规则标签：{message.analysis.topic_tags}

        消息正文：
        {message.message.normalized_content}
        """
    ).strip()


def build_hourly_summary_user_prompt(
    window_start: str,
    window_end: str,
    total_messages: int,
    high_count: int,
    critical_count: int,
    important_messages_json: str,
    clusters_json: str,
    group_stats_json: str,
) -> str:
    return dedent(
        f"""
        请基于下面的数据生成保研小时简报。

        时间窗口：
        - 开始：{window_start}
        - 结束：{window_end}

        统计信息：
        - 总消息数：{total_messages}
        - 高优先级消息数：{high_count}
        - 关键消息数：{critical_count}

        重点消息列表：
        {important_messages_json}

        事件聚合结果：
        {clusters_json}

        按群统计：
        {group_stats_json}

        请特别关注：
        - 老师/导师/学院/实验室
        - 面试/机试/联系导师
        - 截止时间/今晚/明早/尽快
        - 夏令营/预推免/补录/候补
        - 进组/实习/套磁/导师回复/rank/bar/com
        """
    ).strip()


def build_cluster_summary_hint(cluster: MessageCluster) -> str:
    tags = "、".join(cluster.tags[:5]) if cluster.tags else "无"
    return f"{cluster.group_name} 内围绕 {cluster.category} 的讨论，标签：{tags}"

