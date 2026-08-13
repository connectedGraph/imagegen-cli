import os
import sys
import json
import time
import base64
import argparse
import re
import urllib.request
import urllib.parse

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configs.json")

def load_configs():
    if not os.path.exists(CONFIG_FILE):
        print(f"[!] 错误：未找到配置文件 {CONFIG_FILE}")
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def flatten_refs(items):
    """把 --image/--style 的多值 + 逗号分隔展开成路径列表。"""
    out = []
    for it in items or []:
        for p in it.split(","):
            p = p.strip()
            if p:
                out.append(p)
    return out

def image_mime(path):
    """按文件头判断 MIME（png/jpeg/webp，其余兜底 png）。"""
    try:
        with open(path, "rb") as f:
            head = f.read(12)
    except OSError:
        return "image/png"
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if head[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"

def extract_image_from_message(msg):
    """兼容两种返回格式：images 数组（New API 标准）或 content 里的 markdown/base64 图。"""
    imgs = msg.get("images") or []
    if imgs:
        u = imgs[0].get("image_url", {}).get("url", "")
        if "," in u:
            return base64.b64decode(u.split("base64,", 1)[1])
    content = msg.get("content")
    if isinstance(content, str):
        m = re.search(r"data:image/(?:png|jpeg);base64,([A-Za-z0-9+/=]+)", content)
        if m:
            return base64.b64decode(m.group(1))
    elif isinstance(content, list):
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image_url":
                u = part.get("image_url", {}).get("url", "")
                if "," in u:
                    return base64.b64decode(u.split("base64,", 1)[1])
    return None

def parse_args():
    parser = argparse.ArgumentParser(
        description="AI 生图 CLI 工具 (支持图生图)。提示词 100% 原始透传，不修改、不拼接、不加画风后缀。",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""使用示例:
  imagegen 1024x1024 ./cartoon_cat.png "卡通风格的可爱红熊猫"
  imagegen --user user3 --image ref.png 16:9 ./img2img.png "参考图改画风"
  imagegen --image layout.png --image style.png "多图：主图+参考"
  imagegen --image layout.png --style a.png b.png "主图+多风格图"
  imagegen --image a.png,b.png "逗号分隔多图"
  imagegen --config                        # 打印配置文件绝对路径
  imagegen --test                          # 最小请求测试 (无提示词时自带默认提示词)
""",
    )
    parser.add_argument("--user", default=None,
                        help="指定配置用户 (configs.json 里的 id)；省略时用 default_user")
    parser.add_argument("--image", action="append", default=None,
                        help="主参考图路径，可多次传或逗号分隔，启用图生图 (仅 chat_images 协议支持)")
    parser.add_argument("--style", action="append", default=None,
                        help="风格参考图路径，可多次传或逗号分隔，追加为风格参考")
    parser.add_argument("--config", action="store_true",
                        help="仅打印配置文件绝对路径后退出")
    parser.add_argument("--test", action="store_true",
                        help="最小请求测试：未提供提示词时使用内置默认提示词发一次请求，验证 API 配置可用")
    parser.add_argument("args", nargs="*",
                        help="位置参数: [尺寸/比例] [保存路径] [提示词字符串]")

    parsed = parser.parse_args()
    raw_args = parsed.args

    if not raw_args and not parsed.config and not parsed.test:
        parser.print_help()
        print("\n[!] 错误：请输入提示词，或用 --test 发送默认提示词测试。")
        sys.exit(1)

    size_or_ratio = "1024x1024"
    output_path = "output.png"
    prompt = ""

    if len(raw_args) == 1:
        prompt = raw_args[0]
    elif len(raw_args) == 2:
        output_path = raw_args[0]
        prompt = raw_args[1]
    elif len(raw_args) >= 3:
        size_or_ratio = raw_args[0]
        output_path = raw_args[1]
        prompt = " ".join(raw_args[2:])

    image_list = flatten_refs(parsed.image)
    style_list = flatten_refs(parsed.style)

    return parsed.user, image_list, style_list, parsed.config, parsed.test, size_or_ratio, output_path, prompt

def main():
    config_data = load_configs()
    user_flag, image_list, style_list, show_config, test_mode, size_or_ratio, output_path, prompt = parse_args()

    if show_config:
        print(CONFIG_FILE)
        return

    user_id = user_flag if user_flag else config_data.get("default_user", "user1")
    user_config = config_data["users"].get(user_id)

    if not user_config:
        print(f"[!] 未找到指定用户 {user_id} 的配置")
        sys.exit(1)

    if test_mode and not prompt:
        prompt = "test image: a simple red circle on a white background"
        output_path = f"test_{user_id}.png"
        print("[*] 最小请求测试：未提供提示词，使用内置默认提示词")

    headers = {
        "Authorization": f"Bearer {user_config['api_key']}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print(f"[*] 开始生成图片...")
    print(f" |- 当前配置: {user_config['name']} [{user_config['id']}]")
    if image_list or style_list:
        print(f" |- 主参考图 ({len(image_list)}): {image_list}")
        print(f" |- 风格参考图 ({len(style_list)}): {style_list}")
    print(f" |- 提示词: {prompt}")
    print(f" |- 尺寸/比例: {size_or_ratio}")
    print(f" |- 保存路径: {os.path.abspath(output_path)}")

    # Encode all reference images (主图在前, 风格图在后)
    ref_paths = image_list + style_list
    refs = []  # (mime, base64)
    for p in ref_paths:
        if not os.path.exists(p):
            print(f"[!] 参考图不存在: {p}")
            sys.exit(1)
        mime = image_mime(p)
        with open(p, "rb") as f:
            refs.append((mime, base64.b64encode(f.read()).decode("utf-8")))

    if user_config["protocol"] == "openai_images":
        payload = {
            "model": user_config["model"],
            "prompt": prompt,
            "n": 1,
            "size": size_or_ratio
        }
        # openai_images 的 image 字段是数组，支持多参考图
        if refs:
            payload["image"] = [f"data:{m};base64,{b}" for m, b in refs]
    else:
        if refs:
            messages_content = [{"type": "text", "text": prompt}]
            for m, b in refs:
                messages_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{m};base64,{b}"},
                })
        else:
            messages_content = prompt

        payload = {
            "model": user_config["model"],
            "messages": [{"role": "user", "content": messages_content}],
            "aspect_ratio": size_or_ratio
        }

    ctx = urllib.request.ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = urllib.request.ssl.CERT_NONE

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                print(f"[*] 正在尝试第 {attempt} 次重连请求...")
            
            req = urllib.request.Request(user_config["endpoint"], data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')

            with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
                if resp.status != 200:
                    print(f"[!] 请求失败，HTTP 状态码: {resp.status}")
                    sys.exit(1)

                res_data = json.loads(resp.read().decode('utf-8'))
                img_bytes = None

                if user_config["protocol"] == "openai_images":
                    data_list = res_data.get('data', [])
                    if data_list:
                        item = data_list[0]
                        if 'b64_json' in item:
                            img_bytes = base64.b64decode(item['b64_json'])
                        elif 'url' in item:
                            img_req = urllib.request.Request(item['url'], headers={"User-Agent": "Mozilla/5.0"})
                            with urllib.request.urlopen(img_req, context=ctx, timeout=30) as img_resp:
                                img_bytes = img_resp.read()
                else:
                    message = res_data['choices'][0]['message']
                    img_bytes = extract_image_from_message(message)

                if not img_bytes:
                    print("[!] 错误：未能在 API 响应中找到图片数据。响应文本:", json.dumps(res_data, ensure_ascii=False)[:300])
                    sys.exit(1)

                output_dir = os.path.dirname(os.path.abspath(output_path))
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)

                with open(output_path, "wb") as f:
                    f.write(img_bytes)

                print(f"[+] 图片生成成功！已保存至: {os.path.abspath(output_path)}")
                return

        except Exception as e:
            if attempt == max_retries:
                if hasattr(e, 'read'):
                    print("[!] 接口错误:", e.read().decode('utf-8'))
                else:
                    print("[!] 最终失败异常:", e)
                sys.exit(1)
            else:
                time.sleep(2)

if __name__ == "__main__":
    main()
