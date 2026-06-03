# 📚 local-rag-assistant

**プライバシーファーストの完全ローカル文書ナレッジアシスタント。**  
PDF・画像（OCR）・音声/動画文字起こし・YouTube字幕など、手元の文書に質問できます。外部APIへのデータ送信はゼロです。

> 内部コードネーム: *kamikaze*（廃止）

---

## ✨ 特徴

| 機能 | 詳細 |
|------|------|
| **完全ローカル推論** | [Ollama](https://ollama.com) でLLMをローカル実行 |
| **ローカル埋め込み** | `nomic-embed-text` をOllama経由で使用 — 外部埋め込みAPIへの呼び出しゼロ |
| **マルチモーダル取り込み** | PDF・テキスト/Markdown・画像OCR（Tesseract）・音声/動画（faster-whisper）・YouTube（字幕API → Whisperフォールバック） |
| **ChromaDB ベクタDB** | ローカル永続化。クラウド不要 |
| **CHATモード** | 出典付きストリーミングQ&A |
| **REPORTモード** | 一括分析 + PDF出力 |
| **複数セッション管理** | 複数の名前付きチャット履歴をローカルJSONで保存 |
| **クラウドLLM（オプション）** | Anthropic Claudeに切り替え可能（デフォルト: 無効） |

---

## 🏗️ 設計思想

すべてのアーキテクチャ決定の制約は「**機密文書を外部に送り出さない**」という一点でした。

この制約から逆算して各コンポーネントを選定：

- **LLM** → Ollama（ローカル推論サーバー）
- **埋め込み** → `nomic-embed-text` via Ollama（埋め込みAPI呼び出しゼロ）
- **ベクタDB** → ChromaDB（ローカルディレクトリに永続化）
- **OCR** → Tesseract（ローカルバイナリ）
- **音声文字起こし** → faster-whisper（ローカルモデル）

デフォルト設定では、取り込みから回答生成までのデータパイプライン全体がインターネットから完全に切り離されています。

---

## 🚀 クイックスタート

### 1. Ollama のインストールとモデルのダウンロード

```bash
# https://ollama.com からインストール
ollama pull qwen2.5:7b          # 推論LLM（デフォルト）
ollama pull nomic-embed-text    # 埋め込みモデル（必須）
```

### 2. クローンとインストール

```bash
git clone https://github.com/<your-username>/local-rag-assistant.git
cd local-rag-assistant
pip install -e .
```

### 3. 設定

```bash
cp .env.example .env
# モデル名やデータディレクトリを変更したい場合は .env を編集
```

### 4. 起動

```bash
streamlit run src/localrag/ui/app.py
```

http://localhost:8501 を開き、サイドバーの **Start / Restart system** を押してから、**Document library** に文書を追加してください。

---

## 🎬 デモ（サンプルデータ）

`data/samples/` に2種類の中立な合成データが入っています：

- `meeting_notes_sample.md` — 架空のプロジェクトキックオフ議事録
- `product_manual_sample.pdf` — 架空のミドルウェア製品マニュアル

end-to-end デモの手順：

1. システムを起動（サイドバー → **Start / Restart system**）
2. サンプルを取り込む（サイドバー → **Import folder** → `data/samples/` を指定）
3. **Chat** モードで質問する（例：  
   *"キックオフミーティングのアクションアイテムは？"*  
   *"DataBridge Connector の設定方法を教えてください"*）

---

## 🧪 テスト実行

Ollama・Tesseract・ffmpeg なしで全テストが通ります（LLMと埋め込みは決定論的なFakeを注入）。

```bash
pip install -e ".[dev]"
pytest          # 15 tests, all green
```

---

## ⚙️ オプション依存関係

| 機能 | Pythonパッケージ | システム依存 |
|-----|----------------|------------|
| 画像OCR | `pytesseract` | `tesseract-ocr` バイナリ |
| 音声/動画 | `faster-whisper` | 不要（初回使用時にモデルをダウンロード） |
| YouTubeフォールバック | `yt-dlp` | `ffmpeg` バイナリ |
| クラウドLLM | `langchain-anthropic` | `.env` に `ANTHROPIC_API_KEY` |

システム依存が未導入の場合、そのメディアタイプの取り込みのみが**無効化**されます。他のRAG機能は継続して動作します。

---

## 📁 プロジェクト構成

```
local-rag-assistant/
├── src/localrag/
│   ├── config.py              # pydantic-settings 型付きSettings
│   ├── ingestion/             # ローダー: PDF, OCR, Whisper, YouTube
│   ├── rag/                   # チャンク, 埋め込み, LLM, ChromaDB, パイプライン
│   ├── session/               # チャットセッションのJSON永続化
│   └── ui/                    # Streamlit エントリポイント
├── data/
│   └── samples/               # 中立な合成デモ文書
├── tests/                     # pytestスイート（Fake LLM + Fake Embedder）
├── docs/
│   └── architecture.md        # Mermaid アーキテクチャ図
├── .env.example
└── pyproject.toml
```

---

## 🔒 プライバシー保証

`USE_CLOUD_LLM=false`（デフォルト）の場合：

- 文書テキストは外部に送信されない
- 埋め込みベクトルは外部に送信されない
- ChromaDB はすべてのベクトルをローカルに保存
- 外部通信は `localhost` のOllamaのみ

`USE_CLOUD_LLM=true` の場合：クエリテキストがAnthropic APIに送信されます。**埋め込みはこの設定に関わらず常にローカルです。**

---

## 📄 ライセンス

MIT — [LICENSE](LICENSE) を参照。
