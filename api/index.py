from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

FEISHU_APP_ID = "cli_a91d343348389bce"
FEISHU_APP_SECRET = "40CXcUfCrg7Fns8Yi9yXsbg1mvs1tl4h"
KIMI_API_KEY = "sk-ep...t65AB"

@app.route("/", methods=["GET", "POST"])
def webhook():
    # 处理 GET 请求（浏览器访问测试）
    if request.method == "GET":
        return "飞书机器人服务运行中 ✅"
    
    # 处理 POST 请求（飞书回调）
    data = request.get_json() or {}
    
    # 处理飞书验证
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})
    
    # 处理消息
    header = data.get("header", {})
    if header.get("event_type") == "im.message.receive_v1":
        event = data.get("event", {})
        message = event.get("message", {})
        
        if message.get("message_type") == "text":
            content = json.loads(message.get("content", "{}"))
            user_text = content.get("text", "")
            
            # 群聊检查 @
            if message.get("chat_type") == "group":
                mentions = event.get("mentions", [])
                if not mentions:
                    return jsonify({"code": 0})
                for m in mentions:
                    user_text = user_text.replace(m.get("key", ""), "").strip()
            
            # 调用 Kimi
            reply = call_kimi(user_text)
            reply_message(message.get("message_id"), reply)
    
    return jsonify({"code": 0})

def call_kimi(text):
    headers = {
        "Authorization": f"Bearer {KIMI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "moonshot-v1-8k",
        "messages": [{"role": "user", "content": text}]
    }
    resp = requests.post(
        "https://api.moonshot.cn/v1/chat/completions",
        headers=headers, json=data
    )
    return resp.json()["choices"][0]["message"]["content"]

def reply_message(message_id, content):
    token = get_token()
    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    requests.post(url, headers=headers, json={"content": json.dumps({"text": content})})

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    })
    return resp.json()["tenant_access_token"]
