import os
import sys
import json
import time
import base64
import argparse
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

def parse_args():
    parser = argparse.ArgumentParser(
        description="AI 生图 CLI 工具 (支持图生图)。提示词 100% 原始透传，不修改、不拼接、不加画风后缀。",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""使用示例:
  imagegen 1024x1024 ./cartoon_cat.png "卡通风格的可爱红熊猫"
  imagegen --user user2 16:9 ./wallpaper.png "写实风格的夜景城市"
  imagegen --image ref.png 1024x1024 ./img2img.png "参考图改画风"
  imagegen --config                        # 打印配置文件绝对路径
  imagegen --test                          # 最小请求测试 (无提示词时自带默认提示词)
""",
    )
    parser.add_argument("--user", choices=["user1", "user2"], default=None,
                        help="指定配置用户 (user1 或 user2)；省略时用 configs.json 的 default_user")
    parser.add_argument("--image", default=None,
                        help="参考图片路径，启用图生图 (仅 chat_images 协议支持)")
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

    return parsed.user, parsed.image, parsed.config, parsed.test, size_or_ratio, output_path, prompt

def main():
    config_data = load_configs()
    user_flag, input_image_path, show_config, test_mode, size_or_ratio, output_path, prompt = parse_args()

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
    if input_image_path:
        print(f" |- 参考图片: {os.path.abspath(input_image_path)} (图生图)")
    print(f" |- 提示词: {prompt}")
    print(f" |- 尺寸/比例: {size_or_ratio}")
    print(f" |- 保存路径: {os.path.abspath(output_path)}")

    # Encode input image if provided
    base64_image = None
    if input_image_path and os.path.exists(input_image_path):
        with open(input_image_path, "rb") as img_f:
            base64_image = base64.b64encode(img_f.read()).decode('utf-8')

    if user_config["protocol"] == "openai_images":
        payload = {
            "model": user_config["model"],
            "prompt": prompt,
            "n": 1,
            "size": size_or_ratio
        }
    else:
        if base64_image:
            messages_content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                }
            ]
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
                    images = message.get('images', [])
                    if images:
                        b64_str = images[0]['image_url']['url'].split('base64,')[-1]
                        img_bytes = base64.b64decode(b64_str)

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
