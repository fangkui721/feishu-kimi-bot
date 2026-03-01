from flask import Flask, request, jsonify
import json
import requests
import threading

app = Flask(__name__)

FEISHU_APP_ID = "cli_a91d343348389bce"
FEISHU_APP_SECRET = "40CXcUfCrg7Fns8Yi9yXsbg1mvs1tl4h"
KIMI_API_KEY = "sk-SoIbpoJc7WdStDY4vDtAdp8tpIuZRHKOevxO42okCZ9hrZMv"  # 只改这里！

@app.route('/', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        return "OK"
    
    data = request.get_json() or {}
    
    # 验证
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})
    
    # 后台处理
    if data.get("header", {}).get("event_type") == "im.message.receive_v1":
        threading.Thread(target=process, args=(data,)).start()
    
    return jsonify({"code": 0})

def process(data):
    try:
        event = data.get("event", {})
        msg = event.get("message", {})
        
        if msg.get("message_type") != "text":
            return
        
        text = json.loads(msg.get("content", "{}")).get("text", "")
        
        # 群聊去@
        if msg.get("chat_type") == "group":
            mentions = event.get("mentions", [])
            if not mentions:
                return
            for m in mentions:
                text = text.replace(m.get("key", ""), "").strip()
        
        # 调用Kimi
        reply = call_kimi(text)
        
        # 回复飞书
        send_reply(msg.get("message_id"), reply)
        
    except Exception as e:
        print(f"Error: {e}")

def call_kimi(text):
    resp = requests.post(
        "https://api.moonshot.cn/v1/chat/completions",
        headers={"Authorization": f"Bearer {KIMI_API_KEY}", "Content-Type": "application/json"},
        json={"model": "moonshot-v1-8k", "messages": [{"role": "user", "content": text}]},
        timeout=30
    )
    return resp.json()["choices"][0]["message"]["content"]

def send_reply(msg_id, text):
    # 获取token
    token = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET},
        timeout=10
    ).json()["tenant_access_token"]
    
    # 发送回复
    requests.post(
        f"https://open.feishu.cn/open-apis/im/v1/messages/{msg_id}/reply",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"content": json.dumps({"text": text})},
        timeout=10
    )

if __name__ == '__main__':
    app.run()
