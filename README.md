# imagegen-cli

> **A small, configurable image-generation CLI for text-to-image and image-to-image workflows.**<br>
> **一个轻量、可配置的图片生成 CLI，支持文生图与图生图工作流。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-%3E%3D3.8-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)

---

## 中文

### ✨ 简介

`imagegen-cli` 用一个简洁的命令行界面统一管理多个图片生成 API 配置，并把生成结果直接保存到指定路径。它适合个人使用、脚本调用，以及交给 Agent 或自动化工作流执行。

核心原则是：**提示词原样透传**。CLI 不会偷偷添加 `4k`、`masterpiece` 等修饰词，也不会擅自改变你的画风意图。

### 特性

- **多用户配置**：在一个 `configs.json` 中管理多个模型、端点和 API Key。
- **两种 API 协议**：支持 `images/generations` 与 `chat/completions` 风格的图片生成接口。
- **文生图与图生图**：支持单张或多张主参考图，以及额外的风格参考图。
- **顺序可控**：参考图按照「主图在前、风格图在后」的顺序发送给模型。
- **尺寸与比例透传**：支持 `1024x1024`、`16:9`、`9:16` 等参数，交由后端处理。
- **脚本友好**：输出路径自动创建，失败请求自动重试，适合接入 Shell、CI 或 Agent 工作流。
- **零额外依赖**：运行时仅使用 Python 标准库。

### 安装

需要 Python 3.8 或更高版本：

```bash
git clone https://github.com/connectedGraph/imagegen-cli.git
cd imagegen-cli
python3 -m pip install -e . --no-build-isolation
```

安装后即可在任意目录使用 `imagegen` 命令。

### 配置

复制公开模板并填写自己的配置：

```bash
cp configs.example.json configs.json
```

`configs.json` 示例：

```json
{
  "default_user": "openai-user",
  "users": {
    "openai-user": {
      "id": "openai-user",
      "name": "OpenAI-style image endpoint",
      "endpoint": "https://api.example.com/v1/images/generations",
      "api_key": "sk-your-key-here",
      "model": "gpt-image-2",
      "protocol": "openai_images"
    },
    "chat-user": {
      "id": "chat-user",
      "name": "Chat-compatible image endpoint",
      "endpoint": "https://api.example.com/v1/chat/completions",
      "api_key": "sk-your-key-here",
      "model": "gemini-3.1-flash-image",
      "protocol": "chat_images"
    }
  }
}
```

> **安全提示 / Security note**<br>
> `configs.json` 已被 `.gitignore` 忽略。请勿提交包含真实 API Key 的配置文件；公开分享时请使用 `configs.example.json`。

#### 协议选择

| `protocol` | 适用接口 | 参考图支持 |
| --- | --- | --- |
| `openai_images` | `images/generations` 风格接口 | 取决于后端实现；参考图会以 `image` 数组发送 |
| `chat_images` | `chat/completions` 风格多模态接口 | 支持通过 `messages` 中的 `image_url` 发送参考图 |

如果主要需求是图生图，建议优先选择明确支持多模态输入的 `chat_images` 配置，并以实际服务商文档为准。

### 快速开始

#### 文生图

```bash
imagegen 1024x1024 ./outputs/cat.png "一只坐在窗边的红色小熊猫，温暖自然光"
```

#### 指定配置与画幅

```bash
imagegen --user chat-user 16:9 ./outputs/city.png "雨夜中的霓虹城市街道"
```

#### 图生图

```bash
imagegen --user chat-user \
  --image reference.png \
  1024x1024 ./outputs/restyled.png \
  "保留构图与主体，将画面改为复古胶片风格"
```

#### 多张参考图

```bash
# 多张主参考图
imagegen --user chat-user \
  --image layout.png --image subject.png \
  9:16 ./outputs/combined.png \
  "第一张参考布局，第二张参考主体，将两者融合"

# 主图 + 风格参考图
imagegen --user chat-user \
  --image layout.png \
  --style style-a.png --style style-b.png \
  16:9 ./outputs/styled.png \
  "按第一张图的布局，使用其余图片的视觉风格"

# 也可以使用逗号分隔
imagegen --user chat-user --image a.png,b.png \
  ./outputs/multi-ref.png "综合多张参考图生成"
```

#### 测试配置

```bash
# 查看配置文件位置
imagegen --config

# 使用内置提示词发起最小请求
imagegen --test
imagegen --user chat-user --test
```

### 命令格式

```text
imagegen [OPTIONS] [SIZE_OR_RATIO] [OUTPUT_PATH] [PROMPT...]
```

| 参数 | 说明 |
| --- | --- |
| `--user <id>` | 选择 `configs.json` 中的用户；省略时使用 `default_user` |
| `--image <path>` | 主参考图；可重复传入，也可使用逗号分隔多个路径 |
| `--style <path>` | 风格参考图；可重复传入，也可使用逗号分隔多个路径 |
| `--config` | 打印当前配置文件的绝对路径并退出 |
| `--test` | 使用内置提示词发起一次最小请求，验证 API 配置 |
| `SIZE_OR_RATIO` | 例如 `1024x1024`、`16:9`、`9:16`；默认 `1024x1024` |
| `OUTPUT_PATH` | 输出图片路径；默认 `output.png`，缺失目录会自动创建 |
| `PROMPT` | 原样发送给后端的提示词 |

完整参数说明：

```bash
imagegen --help
```

### 处理流程

1. 读取 `configs.json` 并选择用户配置。
2. 将提示词、尺寸/比例和参考图编码为对应协议的请求。
3. 向配置的 API 端点发起请求；失败时最多自动重试 3 次。
4. 从响应中的 Base64 数据或图片 URL 提取结果。
5. 将图片保存到指定路径，并自动创建父目录。

### 项目结构

```text
.
├── generate.py          # CLI 实现
├── configs.example.json # 配置模板
├── pyproject.toml       # Python 包与 CLI 入口
└── LICENSE              # MIT License
```

### 免责声明

本项目只是一个通用 API 客户端，不提供图片生成模型或第三方 API。请遵守所使用服务的条款、版权规则和内容政策，并妥善保护 API Key。

---

## English

### ✨ Overview

`imagegen-cli` provides a compact command-line interface for managing multiple image-generation API profiles and saving generated images directly to a chosen path. It is designed for personal use, shell scripts, Agents, and automation workflows.

The guiding principle is **prompt transparency**: the CLI forwards your prompt as-is. It does not append hidden modifiers such as `4k` or `masterpiece`, and it does not override your artistic intent.

### Features

- **Multiple profiles** — Keep several models, endpoints, and API keys in one `configs.json`.
- **Two API protocols** — Supports `images/generations` and `chat/completions`-style image endpoints.
- **Text-to-image and image-to-image** — Use one or more main references plus optional style references.
- **Deterministic reference order** — Main images are sent first, followed by style images.
- **Transparent sizing** — Pass values such as `1024x1024`, `16:9`, or `9:16` to the backend.
- **Automation-friendly** — Creates missing output directories and retries failed requests automatically.
- **No runtime dependencies** — Uses only the Python standard library.

### Installation

Python 3.8 or newer is required:

```bash
git clone https://github.com/connectedGraph/imagegen-cli.git
cd imagegen-cli
python3 -m pip install -e . --no-build-isolation
```

The `imagegen` command will then be available from any directory.

### Configuration

Copy the public template and fill in your own values:

```bash
cp configs.example.json configs.json
```

Example profile:

```json
{
  "default_user": "chat-user",
  "users": {
    "chat-user": {
      "id": "chat-user",
      "name": "Chat-compatible image endpoint",
      "endpoint": "https://api.example.com/v1/chat/completions",
      "api_key": "sk-your-key-here",
      "model": "gemini-3.1-flash-image",
      "protocol": "chat_images"
    }
  }
}
```

> **Security**<br>
> `configs.json` is ignored by Git. Never commit a file containing a real API key; use `configs.example.json` when sharing configuration publicly.

#### Choosing a protocol

| `protocol` | Endpoint style | Reference-image support |
| --- | --- | --- |
| `openai_images` | `images/generations`-style endpoint | Depends on the provider; references are sent as an `image` array |
| `chat_images` | Multimodal `chat/completions`-style endpoint | References are sent as `image_url` entries in `messages` |

For image-to-image workflows, prefer a `chat_images` profile backed by a provider that explicitly supports multimodal image input. Always follow the provider's documentation.

### Quick start

#### Text-to-image

```bash
imagegen 1024x1024 ./outputs/cat.png "A red panda sitting by a window in warm natural light"
```

#### Select a profile and aspect ratio

```bash
imagegen --user chat-user 16:9 ./outputs/city.png "A neon-lit city street at night in the rain"
```

#### Image-to-image

```bash
imagegen --user chat-user \
  --image reference.png \
  1024x1024 ./outputs/restyled.png \
  "Keep the composition and subject, but restyle the image as vintage film photography"
```

#### Multiple references

```bash
# Multiple main references
imagegen --user chat-user \
  --image layout.png --image subject.png \
  9:16 ./outputs/combined.png \
  "Use the first image for layout and the second for the subject"

# Main image plus style references
imagegen --user chat-user \
  --image layout.png \
  --style style-a.png --style style-b.png \
  16:9 ./outputs/styled.png \
  "Follow the layout of the first image and use the remaining images as style references"

# Comma-separated references are also supported
imagegen --user chat-user --image a.png,b.png \
  ./outputs/multi-ref.png "Generate from multiple references"
```

#### Test a configuration

```bash
# Print the active configuration path
imagegen --config

# Send a minimal request with the built-in test prompt
imagegen --test
imagegen --user chat-user --test
```

### Command reference

```text
imagegen [OPTIONS] [SIZE_OR_RATIO] [OUTPUT_PATH] [PROMPT...]
```

| Option | Description |
| --- | --- |
| `--user <id>` | Select a user from `configs.json`; falls back to `default_user` |
| `--image <path>` | Main reference image; repeat the option or pass comma-separated paths |
| `--style <path>` | Style reference image; repeat the option or pass comma-separated paths |
| `--config` | Print the absolute path of the active configuration file and exit |
| `--test` | Send one minimal request using the built-in test prompt |
| `SIZE_OR_RATIO` | For example `1024x1024`, `16:9`, or `9:16`; defaults to `1024x1024` |
| `OUTPUT_PATH` | Output path; defaults to `output.png`, creating missing directories automatically |
| `PROMPT` | The prompt forwarded to the backend without modification |

For the complete help output:

```bash
imagegen --help
```

### How it works

1. Loads `configs.json` and selects a profile.
2. Encodes the prompt, size/aspect ratio, and references for the selected protocol.
3. Sends the request to the configured API endpoint, retrying up to three times on failure.
4. Extracts the generated image from Base64 data or an image URL in the response.
5. Saves the image to the requested path and creates its parent directory when needed.

### Project structure

```text
.
├── generate.py          # CLI implementation
├── configs.example.json # Configuration template
├── pyproject.toml       # Package metadata and CLI entry point
└── LICENSE              # MIT License
```

### Disclaimer

This project is a general-purpose API client. It does not provide an image-generation model or a third-party API. Follow the terms, copyright rules, and content policies of the services you use, and protect your API keys carefully.

---

## License

[MIT](LICENSE) © 2026 connectedGraph
