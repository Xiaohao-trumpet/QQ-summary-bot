from __future__ import annotations

from app.collector.qq_notification_collector import QQNotificationCollector


def test_parse_group_summary_and_sender_body():
    collector = QQNotificationCollector(allowed_groups=["清华软院预推免群"])

    parsed = collector._parse_notification_payload(
        summary="清华软院预推免群",
        body="李老师：今晚24点前提交材料",
    )

    assert parsed is not None
    assert parsed.group_name == "清华软院预推免群"
    assert parsed.sender_name == "李老师"
    assert parsed.content == "今晚24点前提交材料"


def test_parse_group_embedded_in_summary():
    collector = QQNotificationCollector(allowed_groups=["北大信息学院套磁群"])

    parsed = collector._parse_notification_payload(
        summary="北大信息学院套磁群（学长A）",
        body="建议今晚联系导师",
    )

    assert parsed is not None
    assert parsed.group_name == "北大信息学院套磁群"
    assert parsed.sender_name == "学长A"
    assert parsed.content == "建议今晚联系导师"


def test_group_allowlist_with_contains_mode():
    collector = QQNotificationCollector(
        allowed_groups=["北大信息学院"],
        group_filter_mode="contains",
    )

    assert collector._group_allowed("北大信息学院套磁群") is True
    assert collector._group_allowed("清华软院预推免群") is False


def test_parse_dbus_block_extracts_notification_fields():
    collector = QQNotificationCollector(app_names=["QQ"])
    block = [
        "method call time=1.0 sender=:1.2 -> destination=:1.3 serial=45 path=/org/freedesktop/Notifications; interface=org.freedesktop.Notifications; member=Notify",
        '   string "QQ"',
        "   uint32 0",
        '   string ""',
        '   string "清华软院预推免群"',
        '   string "李老师: 今晚24点前提交材料"',
        "   array [",
        "   ]",
        "   array [",
        "   ]",
        "   int32 -1",
    ]

    event = collector._parse_dbus_block(block)

    assert event is not None
    assert event.app_name == "QQ"
    assert event.summary == "清华软院预推免群"
    assert event.body == "李老师: 今晚24点前提交材料"
