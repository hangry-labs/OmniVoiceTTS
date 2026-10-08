<p align="center">
  <a href="https://hangry-labs.github.io/OmniVoiceTTS/examples/?lang=ja">
    <img src="assets/omnivoice_logo_horizontal.webp" alt="Hangry Labs OmniVoiceTTS ロゴ" width="900">
  </a>
</p>

<p align="center">
  <a href="README.md">English</a> ·
  <a href="README.nb.md">Norsk bokmål</a> ·
  <a href="README.pl.md">Polski</a> ·
  <strong>日本語</strong> ·
  <a href="README.zh.md">简体中文</a> ·
  <a href="README.es.md">Español</a>
</p>

# Hangry Labs OmniVoiceTTS

ローカルのブラウザー UI、HTTP API、音声デザイン、音声クローンを備えた、Docker ですぐに実行できる大規模多言語テキスト読み上げ環境です。

この Hangry Labs 版は、ローカル推論を簡単に利用できるように構成されています。コンテナーを 1 つ起動し、UI を開くか API を呼び出すだけで、Python、モデル、ASR、音声ツールを手動設定せずに音声を生成できます。

## 主な機能

- 音声の生成、ストリーミング、再生、ダウンロードに対応したローカル UI
- OpenAI 互換の `/v1/audio/speech` と完全なネイティブ API
- 自動音声、音声デザイン、直接クローン、保存済み音声プロファイル
- 制御された読み上げと複数話者の会話に対応する標準 SSML および SSML-H
- OmniVoice による 600 以上の言語対応
- WAV、MP3、FLAC、OGG 出力
- ローカル AI エージェント向けの任意の MCP 連携
- ダウンロード後にオフラインで使用できる完全版 Docker イメージ

> [!IMPORTANT]
> ソースコードは Apache-2.0 ですが、事前学習済み OmniVoice チェックポイントは上流で `CC-BY-NC` と説明されており、商用利用は許可されていません。利用または再配布の前に[サードパーティー通知](THIRD_PARTY_NOTICES.md)を確認してください。

## クイックスタート

NVIDIA GPU で完全版イメージを実行します。

```bash
docker run --name omnivoicetts --restart unless-stopped -p 7861:7861 --gpus all -e CUDA_VISIBLE_DEVICES=0 -v omnivoicetts_data:/app/persistent hangrylabs/omnivoicetts:latest
```

このコマンドは 1 行のまま Bash、PowerShell、Windows コマンドプロンプトへ貼り付けられます。名前付きボリュームは Docker が自動的に作成します。

起動後に開くページ:

- ブラウザー UI: [http://localhost:7861](http://localhost:7861)
- API ドキュメント: [http://localhost:7861/tts/docs](http://localhost:7861/tts/docs)
- [言語と音声のサンプル](https://hangry-labs.github.io/OmniVoiceTTS/examples/?lang=ja)

`omnivoicetts_data` ボリュームには、コンテナーの交換やイメージ更新後もモデル、設定、保存済み音声が保持されます。完全版イメージには必要なモデル資産が含まれ、ダウンロード後はオフラインで実行できます。

公開済みの GitHub Release と対応する Git タグは変更できません。バージョン付き Docker イメージタグも変更不可で、`latest` と `latest_tiny` のみが意図的に最新スナップショットへ更新されます。

## 詳細情報

[日本語の製品説明とインストールガイド](https://hangrylabs.app/ja/software/omnivoicetts)をご覧ください。完全な技術資料は[英語版 README](README.md)で管理しています。不具合や提案は [GitHub Issues](https://github.com/Hangry-Labs/OmniVoiceTTS/issues) へ報告してください。
