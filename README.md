# AI 生图 CLI 工具 & 多用户配置指南

这是一个纯净透传的 AI 生图 CLI 工具。用户输入的提示词 **100% 原始透传** 给 API，绝不修改、拼接或改变画风。

支持 **多参考图图生图**：`--image` 可传多个主参考图，`--style` 追加风格参考图，参考图按顺序传给模型（主图在前、风格图在后）。

---

## 📁 配置文件说明 (`configs.json`)

使用前需在脚本所在目录创建 `configs.json`，可直接复制并修改同目录下的 `configs.example.json`：

```json
{
  "default_user": "user1",
  "users": {
    "user1": {
      "id": "user1",
      "name": "用户 A (OpenAI 协议文生图)",
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
    },
    "user3": {
      "id": "user3",
      "name": "用户 C (lt4net gemini 图生图)",
      "endpoint": "https://api.lt4net.org/v1/chat/completions",
      "api_key": "sk-your-key-here",
      "model": "gemini-3.1-flash-image-preview",
      "protocol": "chat_images"
    }
  }
}
```

> ⚠️ `configs.json` 已加入 `.gitignore`（含 API key），请勿提交。公开模板用 `configs.example.json`。

### 协议说明

| protocol | 用途 | 图生图 |
|---|---|---|
| `openai_images` | `images/generations` 端点，文生图（如 gpt-image-2） | ❌ `image` 字段被忽略，参考图无效 |
| `chat_images` | `chat/completions` 端点，多模态生图（如 gemini） | ✅ `messages` 里的 `image_url` 数组，**参考图按布局生效** |

实测：同一张控制图，`openai_images` 生成结果与参考图结构相关性 ≈ 0（参考图被忽略），`chat_images` 相关性 0.23~0.48（按参考图布局生成平台）。**图生图务必用 `chat_images` 用户（如 user3）。**

---

## ⚙️ 提示词与参数处理

- **纯净透传 Prompt**：你传入什么 Prompt，脚本就直接把什么 Prompt 发给 API。不添加 `4k`、`masterpiece` 等任何额外后缀修饰，确保画风完全由你自己掌控。
- **尺寸/比例透传**：直接透传 `size` / `aspect_ratio` 参数给后端。
- **多参考图**：`--image` 与 `--style` 都支持多次传参或用逗号分隔。参考图按「主图在前、风格图在后」顺序填入 `messages`，你可在提示词里描述每张图的作用（如"第一张是布局蓝图，第二张是风格参考"）。

---

## 🚀 命令行使用方法

安装为全局 CLI 后（`python -m pip install -e . --no-build-isolation`），任意目录下直接使用 `imagegen`：

```bash
# 命令格式：imagegen [--user user1|user2|user3] [--image 参考图...] [--style 风格图...] [尺寸/比例] [保存路径] [提示词]

# 示例 1: 纯净生成卡通图（文生图，不改变画风）
imagegen 1024x1024 ./cartoon_cat.png "卡通风格的可爱红熊猫"

# 示例 2: 指定用户 B 生成 16:9 画幅
imagegen --user user2 16:9 ./wallpaper.png "写实风格的夜景城市"

# 示例 3: 图生图（chat_images 协议，user3 = lt4net gemini）
imagegen --user user3 --image ref.png 1024x1024 ./img2img.png "参考图改画风"

# 示例 4: 多主参考图
imagegen --user user3 --image a.png --image b.png 9:16 ./out.png "把两张图融合"

# 示例 5: 主图 + 风格图（结构/布局参考 + 画风参考）
imagegen --user user3 --image layout.png --style style1.png style2.png 9:16 ./out.png \
  "第一张是布局蓝图，其余是风格参考，按蓝图生成地图"

# 示例 6: 逗号分隔多图
imagegen --user user3 --image a.png,b.png 9:16 ./out.png "多图参考"

# 示例 7: 打印配置文件绝对路径
imagegen --config

# 示例 8: 最小请求测试
imagegen --test
imagegen --user user3 --test      # 指定用户测试
```

### 参数说明

| 参数 | 说明 |
| --- | --- |
| `--user <id>` | 指定配置用户（`configs.json` 里的 id）；省略时用 `default_user` |
| `--image <路径>` | **主参考图**，可多次传或逗号分隔多个，启用图生图（仅 `chat_images` 协议生效） |
| `--style <路径>` | **风格参考图**，可多次传或逗号分隔多个，追加为风格参考 |
| `--config` | 仅打印配置文件绝对路径后退出 |
| `--test` | 最小请求测试：未提供提示词时用内置默认提示词发一次请求 |
| `[尺寸/比例]` | 透传给后端，如 `1024x1024`、`16:9`、`9:16` |
| `[保存路径]` | 输出文件路径，自动创建缺失目录 |
| `[提示词]` | 100% 原始透传，不加任何修饰词 |

查看完整帮助：`imagegen --help`
