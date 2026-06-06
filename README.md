# BTC Macro Monitor

ビットコイン短期トレード向けのマクロ・オンチェーン指標監視システム。
新着データや有意な変化を検知したら Discord に通知・AI要約する。

## 監視指標

### Phase 1 — マクロ経済（月次）

| 指標 | ソース | 通知トリガー |
|------|--------|------------|
| CPI（消費者物価指数） | FRED API (CPIAUCSL) | 新しい月次データ |
| NFP（非農業部門雇用者数） | FRED API (PAYEMS) | 新しい月次データ |
| 失業率 | FRED API (UNRATE) | 新しい月次データ |
| 新規失業保険申請件数 | FRED API (ICSA) | 新しい週次データ |
| FOMC議事録/声明文 | federalreserve.gov | 新しいドキュメント |

### Phase 2 — 市場指標（毎時監視）

| 指標 | ソース | 通知トリガー |
|------|--------|------------|
| DXY（ドル指数） | Yahoo Finance | ±0.5%以上の変化 |
| 米国10年債利回り | Yahoo Finance | ±3bp以上の変化 |
| NASDAQ | Yahoo Finance | ±1.0%以上の変化 |
| VIX（恐怖指数） | Yahoo Finance | ±10%以上の変化 |

### Phase 3 — オンチェーン・フロー（日次〜毎時）

| 指標 | ソース | 通知トリガー |
|------|--------|------------|
| SEC新着ファイリング | SEC EDGAR | 新着8-K / S-1 / 19b-4 |
| USDT供給量 | CoinGecko | ±2%以上の変化 |
| USDC供給量 | CoinGecko | ±2%以上の変化 |
| 取引所BTC保有量 | CoinMetrics Community | ±1%以上の変化 |
| M2マネーサプライ | FRED API (M2SL) | 新しい月次データ |
| FRBバランスシート | FRED API (WALCL) | 新しい週次データ |

### Phase 4 — センチメント・デリバティブ（毎時）

| 指標 | ソース | 通知トリガー |
|------|--------|------------|
| 恐怖&強欲指数 | Alternative.me | ゾーン変化（恐怖↔強欲など） |
| 取引所BTC純流入（全取引所） | CoinMetrics Community | 新しい日次データ |
| BTCパーペチュアルFunding Rate | OKX | 符号反転 または ±0.05%閾値越え |

## セットアップ

### 1. リポジトリをGitHubに作成してpush

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/<user>/btc-macro-monitor.git
git push -u origin main
```

### 2. GitHub Secretsを登録

リポジトリの `Settings > Secrets and variables > Actions` から以下を登録：

| Secret名 | 取得元 | 備考 |
|----------|--------|------|
| `FRED_API_KEY` | https://fred.stlouisfed.org/docs/api/api_key.html | 無料 |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ | 従量課金（$5程度で長期利用可） |
| `DISCORD_WEBHOOK_URL` | Discord サーバー設定 → 連携サービス → ウェブフック | 無料 |
| `COINGECKO_API_KEY` | https://www.coingecko.com/en/api → Demo API | 任意・レート制限緩和用 |

### 3. GitHub Actionsを有効化

リポジトリの `Actions` タブでワークフローを有効にする。

手動実行（動作確認）：
```
Actions → BTC Macro Monitor → Run workflow → mode を選択
```

| mode | 実行内容 |
|------|---------|
| `monitor` | Phase 1+2（FRED / FOMC / 市場指標） |
| `glassnode` | Phase 4（Fear&Greed / 取引所BTC純流入 / Funding Rate） |
| `sec` | Phase 3（SEC EDGAR） |
| `stablecoin` | Phase 3（USDT / USDC / 取引所BTC保有量） |
| `liquidity` | Phase 3（M2 / WALCL） |

## 自動実行スケジュール

| 時刻（UTC） | 日本時間 | 実行内容 |
|------------|---------|---------|
| 毎時 :00 | 毎時 9:00〜 | monitor |
| 毎時 :15 | 毎時 9:15〜 | glassnode |
| 毎時 :30 | 毎時 9:30〜 | sec |
| 毎日 0:00 | 毎日 9:00 | stablecoin |
| 毎週水曜 21:00 | 毎週木曜 6:00 | liquidity |

## ローカル実行

```bash
pip install -r requirements.txt

# .envファイルを作成して各APIキーを記入
cp .env.example .env

python main.py --mode monitor
python main.py --mode glassnode
python main.py --mode sec
python main.py --mode stablecoin
python main.py --mode liquidity
```

## ファイル構成

```
btc-macro-monitor/
├── .github/workflows/scheduler.yml  # GitHub Actions（自動実行）
├── fetchers/
│   ├── fred.py                      # FRED API（CPI・NFP・M2・WALCL）
│   ├── fomc.py                      # FOMCスクレイピング
│   ├── market.py                    # Yahoo Finance（DXY・US10Y・NASDAQ・VIX）
│   ├── sec.py                       # SEC EDGAR（8-K・S-1・19b-4）
│   ├── stablecoin.py                # CoinGecko（USDT・USDC）
│   ├── liquidity.py                 # FRED API（M2・WALCL）
│   ├── glassnode.py                 # Alternative.me（Fear&Greed）+ OKX（Funding Rate）
│   └── coinmetrics.py               # CoinMetrics Community（取引所BTC保有量・純流入）
├── detector.py                      # 前回値との差分検知・閾値判定
├── summarizer.py                    # Claude APIで強気/中立/弱気を判定・要約生成
├── notifier.py                      # Discord Webhook通知
├── state.json                       # 前回取得値（Gitで永続化）
├── main.py                          # エントリーポイント
└── requirements.txt
```

## 通知フォーマット

**Claude要約あり（Phase 1・2・4）**
```
【BTC Monitor】CPI（消費者物価指数）
🔴 弱気

CPIが前月比+0.4%と予想を上回る結果。インフレ再燃懸念からFRBの利下げ期待が後退し、
リスク資産全般に売り圧力。BTCは短期的に下押し圧力が強まる可能性が高い。

🔗 https://fred.stlouisfed.org/series/CPIAUCSL
📅 2025-05-14
```

**数値通知（Phase 3 — stablecoin・liquidity）**
```
【BTC Monitor】USDT供給量
📈 増加

現在値: 189.583B USDT
前回比: +2.15%
📅 2025-05-14 09:00 UTC
```

**SEC通知**
```
【BTC Monitor】📋 SEC新着ファイリング
🚨 優先

タイトル: BlackRock Bitcoin ETF Amendment
提出者: BlackRock Inc.
種別: 19b-4

🔗 https://www.sec.gov/...
📅 2025-05-14
```
