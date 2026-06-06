# BTC Macro Monitor

ビットコイン短期トレードの**意思決定補助**を目的としたマクロ・オンチェーン指標監視システム。

マクロ経済・市場・オンチェーン・センチメントの各指標を自動監視し、新着データや有意な変化を検知したら Discord に通知する。各通知には Claude による BTC への影響分析（強気 / 中立 / 弱気）を付与し、エントリー・エグジットの判断材料として活用できる。

## 監視指標

### Phase 1 — マクロ経済

| 指標 | ソース | 頻度 | 通知トリガー |
|------|--------|------|------------|
| CPI（消費者物価指数） | FRED API (CPIAUCSL) | 月次 | 新しいデータ |
| NFP（非農業部門雇用者数） | FRED API (PAYEMS) | 月次 | 新しいデータ |
| 失業率 | FRED API (UNRATE) | 月次 | 新しいデータ |
| 新規失業保険申請件数 | FRED API (ICSA) | 週次 | 新しいデータ |
| FOMC議事録/声明文 | federalreserve.gov | 不定期 | 新しいドキュメント |

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

## 指標の読み方（なぜBTCに効くのか）

通知には Claude による「🟢 強気 / 🟡 中立 / 🔴 弱気」の判定と根拠が付きます。各指標がBTC価格にどう効くか、その「基本の型」を以下にまとめます。実際は複数の要因が絡むため例外もあります。最終判断は Claude の要約コメントと合わせて行ってください。

### 金利・インフレ系（CPI・NFP・失業率・新規失業保険申請・FOMC・米10年債）

**基本の型**: インフレが高い／景気が強い → FRB（米中央銀行）が金利を高く保つ → 預金や国債の魅力が増す → 株やBTCなどのリスク資産から資金が抜ける → **BTCに下押し**。逆に、インフレ鈍化や雇用悪化は利下げ期待につながり **BTCに追い風**。

| 指標 | 動いた向き | BTCへの向き（ざっくり） |
|------|-----------|----------------------|
| CPI（物価）上振れ | インフレ高い | 🔴 弱気寄り（利下げが遠のく） |
| 失業率↑ / NFP下振れ | 景気弱い | 🟢 強気寄り（利下げ期待）※後退懸念が強すぎると逆に売られることも |
| 新規失業保険申請↑ | 労働市場が弱い | 🟢 強気寄り（利下げ期待） |
| 米国10年債利回り↑ | 無リスク金利上昇 | 🔴 弱気寄り（資金が債券へ） |
| FOMC（タカ派＝引き締め寄り） | 金利を高く維持 | 🔴 弱気寄り |

### ドル・株・恐怖指数（DXY・NASDAQ・VIX）

| 指標 | 動いた向き | BTCへの向き |
|------|-----------|------------|
| DXY（ドル指数）↑ | ドル高 | 🔴 弱気寄り（ドル建て資産に逆風） |
| NASDAQ↑ | ハイテク株高 | 🟢 強気寄り（BTCはリスクオンで連動しやすい） |
| VIX（恐怖指数）急騰 | 市場が恐怖 | 🔴 弱気寄り（リスク回避で資金逃避）※急騰時は🚨優先通知 |

### お金の量（M2・FRBバランスシート・USDT/USDC供給量）

**基本の型**: 世の中に出回るお金が増える → 余ったお金がリスク資産に向かう → **BTCに追い風**。

| 指標 | 動いた向き | BTCへの向き |
|------|-----------|------------|
| M2マネーサプライ↑ / FRBバランスシート拡大 | 金融緩和 | 🟢 強気寄り |
| USDT・USDC供給量↑ | 暗号資産市場の待機資金が増加 | 🟢 強気寄り（減少は🔴弱気寄り） |

### オンチェーン・需給（取引所BTC保有量・純流入・Funding Rate・恐怖&強欲指数）

| 指標 | 動いた向き | BTCへの向き |
|------|-----------|------------|
| 取引所BTC保有量↑ / 純流入↑ | 売る準備のBTCが取引所に集まる | 🔴 弱気寄り（純流出は🟢強気寄り＝長期保有へ） |
| Funding Rate 大きくプラス | ロング（買い持ち）が過熱 | ⚠️ 急落（ロング・スクイーズ）に注意。マイナスへ反転は底打ちの兆候になり得る |
| 恐怖&強欲指数 | 市場心理 | **逆張り指標**: 「極度の恐怖」は買い場の候補、「極度の強欲」は過熱・調整警戒 |

## 限界と免責

- 本システムは**意思決定の補助**であって、売買シグナルではありません。最終判断は必ずご自身で行ってください。
- **指標にはラグがあります**。CPIや雇用統計は月1回・数週間遅れ、M2は月次。発表時点で既に価格へ織り込み済みのこともあります。
- **しきい値（±0.5% など）は経験則**です。相場環境によって最適値は変わります。`config.py` でいつでも調整できます（小さくすると通知が増え、大きくすると減ります）。
- **「強気/中立/弱気」は Claude（AI）による確率的な推定**で、外れることがあります。
- データは**無料API**に依存しており、提供側の仕様変更や一時障害で取得が止まる場合があります（その際はエラー通知が届きます）。
- 暗号資産は価格変動が非常に大きく、本システムは損失を防ぐものではありません。**投資は自己責任**で行ってください。

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
│   ├── fred.py                      # FRED API（CPI・NFP・失業率・新規申請件数・M2・WALCL）
│   ├── fomc.py                      # FOMCスクレイピング
│   ├── market.py                    # Yahoo Finance（DXY・US10Y・NASDAQ・VIX）
│   ├── sec.py                       # SEC EDGAR（8-K・S-1・19b-4）
│   ├── stablecoin.py                # CoinGecko（USDT・USDC）
│   ├── glassnode.py                 # Alternative.me（Fear&Greed）+ OKX（Funding Rate）
│   └── coinmetrics.py               # CoinMetrics Community（取引所BTC保有量・純流入）
├── config.py                        # 通知しきい値の一元管理（編集して感度を調整）
├── detector.py                      # 前回値との差分検知・閾値判定
├── summarizer.py                    # Claude APIで強気/中立/弱気を判定・要約生成
├── notifier.py                      # Discord Webhook通知
├── state.json                       # 前回取得値（Gitで永続化）
├── main.py                          # エントリーポイント
└── requirements.txt
```

## 通知フォーマット

**Claude要約あり（Phase 1・2・3・4）**
```
【BTC Monitor】CPI（消費者物価指数）
🔴 弱気

CPIが前月比+0.4%と予想を上回る結果。インフレ再燃懸念からFRBの利下げ期待が後退し、
リスク資産全般に売り圧力。BTCは短期的に下押し圧力が強まる可能性が高い。

🔗 https://fred.stlouisfed.org/series/CPIAUCSL
📅 2025-05-14
```

**SEC通知（Claude要約あり）**
```
【BTC Monitor】📋 SEC新着ファイリング
🚨 優先

タイトル: BlackRock Inc. [19b-4]
提出者: BlackRock Inc.
種別: 19b-4

🟢 強気
BlackRockによる19b-4提出はビットコインETF関連の規制申請。
承認されれば機関資金の大規模流入が見込まれ、短期的に強い買い圧力となる。

🔗 https://www.sec.gov/...
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
