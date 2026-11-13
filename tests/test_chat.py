"""A YouTube live chat line becomes (unix time, text). Run: python tests/test_chat.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from clipforge.source import live_chat_line  # noqa: E402

msg = {"liveChatTextMessageRenderer": {"message": {"runs": [{"text": "NO WAY "}, {"text": "he crashed"}]},
                                       "timestampUsec": "1794567267698490"}}
line = json.dumps({"replayChatItemAction": {"actions": [{"addChatItemAction": {"item": msg}}, {"other": 1}]}})
assert live_chat_line(line) == [(1794567267.69849, "NO WAY he crashed")], live_chat_line(line)
assert live_chat_line("not json") == [] and live_chat_line("{}") == []
print("ok")
