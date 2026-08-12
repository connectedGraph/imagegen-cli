# AI 生图 CLI 工具 & 多用户配置指南

这是一个纯净透传的 AI 生图 CLI 工具。用户输入的提示词 **100% 原始透传** 给 API，绝不修改、拼接或改变画风。

---

## 📁 配置文件说明 (`configs.json`)

使用前需在脚本所在目录创建 `configs.json`，可直接复制并修改同目录下的 `configs.example.json`：

```json
{
  "default_user": "user1",
  "users": {
    "user1": {
      "id": "user1",
      "name": "用户 A (OpenAI 协议生图网关)",
      "endpoint": "https://api.example.com/v1/images/generations",
      "api_key": "sk-your-key-here",
      "model": "gpt-image-2",
      "protocol": "openai_images"
    },
    "user2": {
      "id": "user2",
      "name": "用户 B (Chat 协议生图网关)",
      "endpoint": "https://api.example.com/v1/chat/completions",
      "api_key": "sk-your-key-here",
      "model": "gemini-3.1-flash-image",
      "protocol": "chat_images"
    }
  }
}
```

---

## ⚙️ 提示词与参数处理

- **纯净透传 Prompt**：你传入什么 Prompt，脚本就直接把什么 Prompt 发给 API。不添加 `4k`、`masterpiece` 等任何额外后缀修饰，确保画风（卡通、写实、手绘等）完全由你自己掌控。
- **尺寸/比例透传**：直接透传 `size` / `aspect_ratio` 参数给后端。

---

## 🚀 命令行使用方法

安装为全局 CLI 后（`python -m pip install -e . --no-build-isolation`），任意目录下直接使用 `imagegen`：

```bash
# 命令格式：imagegen [--user user1|user2] [--image 参考图] [尺寸/比例] [保存路径] [提示词]

# 示例 1: 纯净生成卡通图（不改变画风）
imagegen 1024x1024 ./cartoon_cat.png "卡通风格的可爱红熊猫"

# 示例 2: 使用用户 B 配置生成 16:9 画幅
imagegen --user user2 16:9 ./wallpaper.png "写实风格的夜景城市"

# 示例 3: 图生图（chat_images 协议）
imagegen --image ref.png 1024x1024 ./img2img.png "参考图改画风"

# 示例 4: 打印配置文件绝对路径
imagegen --config

# 示例 5: 最小请求测试（未提供提示词时自动用默认提示词，验证 API 配置可用）
imagegen --test
imagegen --user user2 --test        # 指定用户测试
```

参数说明：

| 参数 | 说明 |
| --- | --- |
| `--user user1\|user2` | 指定配置用户；省略时用 `configs.json` 的 `default_user` |
| `--image <路径>` | 参考图片，启用图生图（仅 chat_images 协议支持） |
| `--config` | 仅打印配置文件绝对路径后退出 |
| `--test` | 最小请求测试：未提供提示词时用内置默认提示词发一次请求 |
| `[尺寸/比例]` | 透传给后端，如 `1024x1024`、`16:9` |
| `[保存路径]` | 输出文件路径，自动创建缺失目录 |
| `[提示词]` | 100% 原始透传，不加任何修饰词 |

查看完整帮助：`imagegen --help`

