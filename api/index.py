from http.server import BaseHTTPRequestHandler
import json
import requests

# ==================== 配置区域 ====================
FEISHU_APP_ID = "cli_a91d343348389bce"
FEISHU_APP_SECRET = "40CXcUfCrg7Fns8Yi9yXsbg1mvs1tl4h"
KIMI_API_KEY = "sk-ep...t65AB"  # 替换为你的完整 Kimi API Key
# =================================================

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            print(f"📨 收到请求: {json.dumps(data, ensure_ascii=False)[:200]}...")
            
            # 处理飞书验证请求
            if "challenge" in data:
                print(f"✅ 处理验证请求")
                self._send_json({"challenge": data["challenge"]})
                return
            
            # 处理消息事件
            header = data.get("header", {})
            if header.get("event_type") == "im.message.receive_v1":
                self._handle_message(data)
            
            # 立即返回成功（飞书要求3秒内响应）
            self._send_json({"code": 0, "msg": "success"})
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            self._send_json({"code": 500, "msg": str(e)}, 500)
    
    def _handle_message(self, data):
        """处理消息"""
        try:
            event = data.get("event", {})
            message = event.get("message", {})
            
            # 只处理文本消息
            if message.get("message_type") != "text":
                print("⏭️ 非文本消息，跳过")
                return
            
            # 解析消息内容
            content = json.loads(message.get("content", "{}"))
            user_text = content.get("text", "")
            
            # 群聊需要判断是否 @机器人
            if message.get("chat_type") == "group":
                mentions = event.get("mentions", [])
                if not mentions:
                    print("⏭️ 群消息未 @机器人，跳过")
                    return
                # 去掉 @机器人的标记
                for m in mentions:
                    user_text = user_text.replace(m.get("key", ""), "").strip()
                
                print(f"💬 群消息: {user_text[:50]}...")
            else:
                print(f"💬 单聊消息: {user_text[:50]}...")
            
            # 调用 Kimi API
            reply = call_kimi(user_text)
            print(f"🤖 Kimi回复: {reply[:100]}...")
            
            # 回复飞书
            reply_message(message.get("message_id"), reply)
            print("✅ 回复成功")
            
        except Exception as e:
            print(f"❌ 处理消息失败: {e}")
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def call_kimi(text):
    """调用 Kimi API"""
    headers = {
        "Authorization": f"Bearer {KIMI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "moonshot-v1-8k",
        "messages": [
            {
                "role": "system", 
                "content": "你是 Kimi 助手，一个 helpful、专业的 AI 助手。请用中文回答。"
            },
            {
                "role": "user", 
                "content": text
            }
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    resp = requests.post(
        "https://api.moonshot.cn/v1/chat/completions",
        headers=headers, 
        json=data, 
        timeout=30
    )
    
    result = resp.json()
    if "choices" not in result:
        raise Exception(f"Kimi API 错误: {result}")
    
    return result["choices"][0]["message"]["content"]


def reply_message(message_id, content):
    """回复飞书消息"""
    token = get_feishu_token()
    
    url = f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "content": json.dumps({"text": content})
    }
    
    resp = requests.post(url, headers=headers, json=data, timeout=10)
    result = resp.json()
    
    if result.get("code") != 0:
        raise Exception(f"回复失败: {result}")


def get_feishu_token():
    """获取飞书 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    
    resp = requests.post(url, json={
        "app_id": FEISHU_APP_ID,
        "app_secret": FEISHU_APP_SECRET
    }, timeout=10)
    
    result = resp.json()
    if result.get("code") != 0:
        raise Exception(f"获取 token 失败: {result}")
    
    return result["tenant_access_token"]
