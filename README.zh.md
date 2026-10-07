<p align="center">
  <a href="https://hangry-labs.github.io/OmniVoiceTTS/examples/?lang=zh">
    <img src="assets/omnivoice_logo_horizontal.webp" alt="Hangry Labs OmniVoiceTTS 标志" width="900">
  </a>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.nb.md">Norsk bokmål</a> ·
  <a href="README.pl.md">Polski</a> ·
  <a href="README.ja.md">日本語</a> ·
  <strong>简体中文</strong> ·
  <a href="README.es.md">Español</a>
</p>

# Hangry Labs OmniVoiceTTS

可直接通过 Docker 运行的大规模多语言文本转语音环境，内置本地浏览器界面、HTTP API、声音设计和声音克隆功能。

Hangry Labs 版本专注于简单的本地推理。只需启动一个容器，然后打开界面或调用 API，即可生成语音，无需手动配置 Python、模型、ASR 或音频工具。

## 项目功能

- 用于生成、流式播放、回放和下载音频的本地浏览器界面
- 兼容 OpenAI 的 `/v1/audio/speech` 端点和完整的原生 API
- 自动声音、声音设计、直接克隆和已保存的声音配置
- 用于可控语音和多角色对话的标准 SSML 与 SSML-H
- 继承自 OmniVoice 的 600 多种语言支持
- WAV、MP3、FLAC 和 OGG 输出
- 面向本地 AI 智能体的可选 MCP 集成
- 下载后可离线运行的完整 Docker 镜像

> [!IMPORTANT]
> 源代码采用 Apache-2.0 许可证，但上游将预训练 OmniVoice 检查点标记为 `CC-BY-NC`，因此不允许商业使用。使用或重新分发之前，请阅读[第三方声明](THIRD_PARTY_NOTICES.md)。

## 快速开始

使用 NVIDIA GPU 运行完整镜像：

```bash
docker run --name omnivoicetts --restart unless-stopped -p 7861:7861 --gpus all -e CUDA_VISIBLE_DEVICES=0 -v omnivoicetts_data:/app/persistent hangrylabs/omnivoicetts:latest
```

此命令为单行格式，可直接粘贴到 Bash、PowerShell 或 Windows 命令提示符中。Docker 会自动创建命名卷。

启动后打开：

- 浏览器界面：[http://localhost:7861](http://localhost:7861)
- API 文档：[http://localhost:7861/tts/docs](http://localhost:7861/tts/docs)
- [语言和声音示例](https://hangry-labs.github.io/OmniVoiceTTS/examples/?lang=zh)

`omnivoicetts_data` 卷会在容器替换或镜像更新后继续保留模型、设置和已保存声音。完整镜像包含所需模型资源，下载后可以离线运行。

## 更多信息

请查看[完整的中文产品介绍和安装指南](https://hangrylabs.app/zh/software/omnivoicetts)。完整技术参考由[英文 README](README.md)维护。错误和建议可提交到 [GitHub Issues](https://github.com/Hangry-Labs/OmniVoiceTTS/issues)。
