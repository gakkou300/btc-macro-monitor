# BTC Macro Monitor

ビットコイン短期トレード向けのマクロ指標監視システム。
新着データを検知したらLINEに通知・要約する。

## 監視指標（Phase 1）

| 指標 | ソース | 更新頻度 |
|------|--------|----------|
| CPI（消費者物価指数） | FRED API (CPIAUCSL) | 月次 |
| NFP（非農業部門雇用者数） | FRED API (PAYEMS) | 月次 |
| FOMC議事録/声明文 | federalreserve.gov | 年8回 |

## セットアップ

### 1. リポジトリをGitHubに作成してpush

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/<user>/btc-monitor.git
git push -u origin main
```

### 2. GitHub Secretsを登録

リポジトリの `Settings > Secrets and variables > Actions` から以下を登録：

| Secret名 | 取得元 | 備考 |
|----------|--------|------|
| `FRED_API_KEY` | https://fred.stlouisfed.org/docs/api/api_key.html | 無料 |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ | 従量課金（$5で数年分） |
| `DISCORD_WEBHOOK_URL` | Discord サーバー設定 → 連携サービス → ウェブフック | 無料 |
| `GLASSNODE_API_KEY` | https://studio.glassnode.com/settings/api → Sign Up → API Keys | 無料枠あり |
| `COINGECKO_API_KEY` | https://www.coingecko.com/en/api → Demo API | 任意・レート制限緩和用 |
| `LINE_NOTIFY_TOKEN` | https://notify-bot.line.me/my/ |

### 3. GitHub Actionsを有効化

リポジトリの `Actions` タブでワークフローを有効にする。
`workflow_dispatch` から手動実行して動作確認できる。

## ローカル実行

```bash
pip install -r requirements.txt

# .envファイルを作成
cp .env.example .env
# .envに各APIキーを記入

python main.py
```

## ファイル構成

```
btc-monitor/
├── .github/workflows/scheduler.yml  # GitHub Actions（毎時実行）
├── fetchers/
│   ├── fred.py                      # FRED API（CPI・NFP）
│   └── fomc.py                      # FOMCスクレイピング
├── detector.py                      # 前回値との差分検知
├── summarizer.py                    # Claude APIで要約生成
├── notifier.py                      # LINE Notify通知
├── state.json                       # 前回取得値（Gitで永続化）
├── main.py                          # エントリーポイント
└── requirements.txt
```

## 拡張方法（Phase 2以降）

`fetchers/` に新しいファイルを追加し、`main.py` で呼び出すだけで拡張できる。

```python
# fetchers/binance.py を追加した場合
from fetchers.binance import fetch_funding_rate

def run_binance() -> None:
    ...
```

## 通知フォーマット

```
【BTC Monitor】CPI (消費者物価指数)
🔴 弱気

CPIが前月比+0.4%と予想を上回る結果。インフレ再燃懸念からFRBの利下げ期待が後退し、
リスク資産全般に売り圧力。BTCは短期的に下押し圧力が強まる可能性が高い。

🔗 https://fred.stlouisfed.org/series/CPIAUCSL
📅 2025-05-14
```
