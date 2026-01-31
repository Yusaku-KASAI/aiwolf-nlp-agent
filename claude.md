# AIWolf NLP Agent - Claude開発者用ドキュメント

## 目次
1. [プロジェクト概要](#プロジェクト概要)
2. [人狼ゲームのルール](#人狼ゲームのルール)
3. [システムアーキテクチャ](#システムアーキテクチャ)
4. [エージェント実装](#エージェント実装)
5. [開発の進捗状況](#開発の進捗状況)
   - [✅ 完了済みの改善](#完了済みの改善)
   - [📊 実行結果サマリー](#実行結果サマリー)
   - [🐛 現在の問題点](#現在の問題点)
   - [🎯 今後の改善計画](#今後の改善計画)
6. [開発Tips](#開発tips)

---

## プロジェクト概要

### 基本情報
- **プロジェクト名**: aiwolf-nlp-agent-llm
- **目的**: 人狼知能コンテスト（自然言語部門）のLLMベースエージェント
- **言語**: Python 3.11+
- **LLM対応**: OpenAI, Google Gemini, Ollama, その他
- **公式サイト**: https://aiwolfdial.github.io/aiwolf-nlp/

### ディレクトリ構造
```
aiwolf-nlp-agent/
├── src/
│   ├── agent/          # エージェント実装
│   │   ├── agent.py    # 基底クラス
│   │   ├── seer.py     # 占い師
│   │   ├── werewolf.py # 人狼
│   │   ├── villager.py # 村人
│   │   ├── possessed.py # 狂人
│   │   ├── medium.py   # 霊媒師
│   │   └── bodyguard.py # 騎士
│   ├── main.py         # エントリポイント
│   ├── starter.py      # 接続・ゲームセッション管理
│   └── utils/          # ユーティリティ
├── config/
│   ├── config.yml      # メイン設定ファイル
│   └── .env           # API キー等
└── log/               # ゲームログ

../aiwolf-nlp-server/  # ゲームサーバ (Go実装)
├── config/
│   ├── default_5.yml  # 5人村設定
│   └── default_13.yml # 13人村設定
└── main.go
```

---

## 人狼ゲームのルール

### 基本概要
- **陣営**: 村人陣営 vs 人狼陣営
- **目標**:
  - 村人陣営: 人狼を全滅させる
  - 人狼陣営: 村人を人狼と同数以下にする

### 役職構成

#### 5人村
| 役職 | 人数 | 陣営 | 能力 |
|------|------|------|------|
| 村人 (VILLAGER) | 2 | 村人 | 特殊能力なし |
| 占い師 (SEER) | 1 | 村人 | 毎晩1人を占い、人狼か否か判明 |
| 人狼 (WEREWOLF) | 1 | 人狼 | 毎晩1人を襲撃、人狼同士で囁ける |
| 狂人 (POSSESSED) | 1 | 人狼 | 人狼陣営だが人狼を知らない、占われると村人判定 |

#### 13人村
5人村の構成に加えて:
| 役職 | 人数 | 陣営 | 能力 |
|------|------|------|------|
| 霊媒師 (MEDIUM) | 1 | 村人 | 処刑された人が人狼か否か判明 |
| 騎士 (BODYGUARD) | 1 | 村人 | 毎晩1人を護衛、襲撃から守る |
| 村人 | 6 | 村人 | (5人村より4人増) |
| 人狼 | 3 | 人狼 | (5人村より2人増) |

### ゲームの流れ

#### 1日の流れ
```
0日目（初日）
  └─ 朝: 役職配布、初回会話（囁き可能）
  └─ 夜: 占い（処刑なし）

1日目以降
  ├─ 朝 (DAILY_INITIALIZE)
  │   ├─ 前日の処刑結果発表
  │   ├─ 夜の襲撃結果発表
  │   ├─ 占い結果（自分のみ）
  │   └─ 霊媒結果（自分のみ）
  │
  ├─ 昼 (TALK)
  │   ├─ 議論フェーズ
  │   ├─ 発言回数制限: 1人4回まで、全体20回まで
  │   ├─ 文字数制限: 125文字（超過は切り捨て）
  │   └─ 発言終了: "Over" で打ち切り
  │
  ├─ 投票 (VOTE)
  │   └─ 全員が1人を指定（最多得票者を処刑）
  │
  └─ 夜
      ├─ 占い (DIVINE) - 占い師のみ
      ├─ 護衛 (GUARD) - 騎士のみ
      ├─ 囁き (WHISPER) - 人狼のみ
      └─ 襲撃 (ATTACK) - 人狼のみ
```

### 勝利条件

#### 村人陣営の勝利
- 人狼が全滅した時点

#### 人狼陣営の勝利
- 人狼の数 ≧ 村人陣営の数になった時点

### 重要な制約

1. **自然言語のみ**: プロトコル使用禁止
2. **文字数制限**: 1発話125文字（超過は自動カット）
3. **発言制限**:
   - 1人あたり: 最大4回/日
   - 全体: 最大20回/日
4. **応答時間**: 各アクション60秒以内
5. **カンマ禁止**: 発話にカンマは含められない
6. **顔文字・絵文字非推奨**: 音声再生非対応

---

## システムアーキテクチャ

### 通信プロトコル

#### WebSocket接続
```
エージェント ←→ WebSocket (ws://server:8080/ws) ←→ ゲームサーバ
```

#### リクエスト・レスポンス形式

**サーバーからエージェントへ**: JSON形式のPacket
```json
{
  "request": "TALK",
  "info": {
    "game_id": "...",
    "day": 1,
    "agent": "ミナコ",
    "status_map": {"アスカ": "ALIVE", ...},
    "role_map": {"ミナコ": "WEREWOLF"}
  },
  "setting": {...},
  "talk_history": [...]
}
```

**エージェントからサーバーへ**: 文字列
- TALK/WHISPER: 日本語の発言 or "Over"
- VOTE/DIVINE/ATTACK/GUARD: エージェント名のみ

### リクエストの種類

| リクエスト | 説明 | 期待される応答 |
|------------|------|----------------|
| NAME | 名前要求 | エージェント名 |
| INITIALIZE | ゲーム開始 | プロンプトに基づく初期化 |
| DAILY_INITIALIZE | 朝の開始 | なし（内部状態更新） |
| TALK | 発言要求 | 日本語発言 or "Over" |
| WHISPER | 囁き要求（人狼） | 日本語発言 or "Over" |
| VOTE | 投票要求 | エージェント名 |
| DIVINE | 占い要求（占い師） | エージェント名 |
| GUARD | 護衛要求（騎士） | エージェント名 |
| ATTACK | 襲撃要求（人狼） | エージェント名 |
| DAILY_FINISH | 昼の終了 | なし |
| FINISH | ゲーム終了 | なし |

---

## エージェント実装

### クラス構造

```python
Agent (基底クラス)
  ├─ Villager (村人)
  ├─ Seer (占い師)
  ├─ Medium (霊媒師)
  ├─ Bodyguard (騎士)
  ├─ Werewolf (人狼)
  └─ Possessed (狂人)
```

### 主要メソッド

#### Agent基底クラス
```python
class Agent:
    def __init__(self, config, name, game_id, role):
        self.llm_model = ...  # LLMモデル
        self.llm_message_history = []  # 会話履歴
        self.info = None  # 現在の状態
        self.setting = None  # ゲーム設定

    def _send_message_to_llm(self, request) -> str:
        """LLMにプロンプトを送信して応答を取得"""

    def _parse_agent_name(self, response) -> str:
        """LLMの応答からエージェント名を抽出・検証"""

    def talk(self) -> str:
        """発言生成"""

    def vote(self) -> str:
        """投票先を決定"""

    def divine(self) -> str:
        """占い先を決定（占い師のみ）"""

    def attack(self) -> str:
        """襲撃先を決定（人狼のみ）"""

    def guard(self) -> str:
        """護衛先を決定（騎士のみ）"""
```

### プロンプト設計

#### プロンプトテンプレート (config/config.yml)

```yaml
prompt:
  initialize: |-
    あなたは人狼ゲームのエージェントです。
    あなたの名前は{{ info.agent }}です。
    あなたの役職は{{ role.value }}です。

  talk: |-
    トークリクエスト
    履歴:
    {% for w in talk_history[sent_talk_count:] -%}
    {{ w.agent }}: {{ w.text }}
    {% endfor %}

  vote: |-
    投票リクエスト
    以下の生存者の中から1人を選んで、その名前のみを出力してください。
    説明や句読点は不要です。名前だけを出力してください。

    対象:
    {% for k, v in info.status_map.items() -%}
    {%- if v == 'ALIVE' -%}
    {{ k }}
    {% endif -%}
    {%- endfor %}
```

### LLMモデル設定

#### サポートされるLLM
```yaml
llm:
  type: dmr  # dmr, openai, google, ollama

openai:
  model: gpt-4o-mini
  temperature: 0.7

google:
  model: gemini-2.0-flash-lite
  temperature: 0.7

ollama:
  model: llama3.1
  base_url: http://localhost:11434

dmr:
  model: ai/gemma3:latest
  base_url: http://model-runner.docker.internal/engines/v1
```

---

## 開発の進捗状況

### ✅ 完了済みの改善

#### フェーズ1: 基本システム実装
1. **エージェント名パース機能** (agent.py `_parse_agent_name()`)
   - LLMの不正な応答からエージェント名を抽出
   - 無効な応答時のフォールバック処理（ランダム選択）
   - ゲームが正常に終了するようになった

2. **メモリシステム実装** (memory.py `MemorySystem`)
   - 役職CO、占い/霊媒結果、投票履歴の記録
   - 矛盾検出機能
   - 疑惑スコア計算

3. **発言パーサー実装** (talk_parser.py `TalkParser`)
   - 役職COの抽出（正規表現）
   - 占い結果の抽出
   - 霊媒結果の抽出

#### フェーズ2: 占い師機能強化
4. **占い師CO機能実装** (seer.py)
   - `should_claim_seer()`: CO判定ロジック
   - `create_co_message()`: CO発言生成
   - `create_divine_result_message()`: 結果報告生成
   - `talk()`: 自動CO実行

5. **早期Over防止機能** (agent.py)
   - `my_talk_count_today`: 発言カウンター
   - 2回未満の発言でOverを防止
   - `_generate_fallback_talk()`: フォールバック発言

#### フェーズ3: バグ修正と戦略改善
6. **Species型比較バグ修正（完全版）** (agent.py:366, 378; seer.py:207)
   - `.name` プロパティを使用して正しくEnum比較
   - 占い結果が正確に判定されるようになった

7. **自己占いバグ修正** (seer.py divine())
   - 自分自身を占い対象から除外
   - `info.agent` を使用して正確な自分の名前を取得

8. **CO条件変更** (seer.py should_claim_seer())
   - Day 2 → Day 1 に変更（早期CO戦略）
   - 襲撃される前に情報を共有

#### フェーズ4: プロンプト改善
9. **プロンプト大幅改善** (config.yml)
   - ゲームの本質（役職推理・矛盾検出・投票戦略）を明示
   - 禁止事項を明確化（アリバイ、無意味な会話）
   - 役職ごとの具体的戦略を追加
   - アクションプロンプトの改善（vote, divine, attack, guard）

---

### 📊 実行結果サマリー

#### 第1回実行 (log/20260131104130803/)
**状態**: メモリシステム・発言パーサー実装前
**結果**: ゲーム終了せず

**主な問題**:
- 占い師が役職COをしない
- 発言が浅く戦略性が低い
- エージェント名パース失敗によりゲームが進行しない

#### 第2回実行 (log/20260131110735209/)
**状態**: 占い師CO機能実装、Species比較にバグあり
**結果**: 人狼陣営の勝利

**タイムライン**:
- 0日目夜: ミヅキ（占い師）が自分自身を占う ← バグ
- 1日目: COせず（divine_resultsが空のため）
- 1日目夜: ダイスケ（人狼）を占う → 人狼判定
- 2日目朝: ミヅキ襲撃されて死亡 → 情報を報告できず

**問題点**:
- 自己占いバグ
- Species型比較バグ（Enum vs String）
- Day 2までCO待機 → 襲撃される

#### 第3回実行 (log/20260131114137368/) ⭐ 最新
**状態**: 自己占い修正、Day 1 CO実装、プロンプト改善、Species比較に不完全な修正
**結果**: 村人陣営の勝利

**タイムライン**:
- 0日目: ジョージが幻覚でCO（まだ占い結果がないのに）
- 0日目夜: ジョナサン（人狼）を占う → 人狼判定
- 1日目: ジョージがCO、「ジョナサンは村人」と誤報告 ← Enumバグ
- 1日目: ジョナサン処刑（偶然正しい結果）

**良い点**:
- ✅ 占い師がCOした
- ✅ Day 1でCOが発動
- ✅ 自己占いバグ修正済み
- ✅ プロンプト改善の効果あり

**問題点**:
- 🐛 占い結果が逆に報告される（Enumバグ未修正）
- 🤖 Day 0での幻覚
- 😵 人狼が自己処刑を提案
- 🔁 同じ発言を4回繰り返す
- ✂️ 125文字制限で文章が途切れる

---

### 🐛 現在の問題点

#### クリティカル（ゲームプレイに影響）

1. **発言の重複** 🔁
   - **症状**: 同じ占い結果を4回報告
   - **原因**: `create_divine_result_message()` が報告済みフラグを持たない
   - **影響**: 発言枠の無駄遣い、情報の陳腐化

2. **Day 0での幻覚** 🤖
   - **症状**: まだ起きていないことを話す（「占い結果」「夜の行動」など）
   - **原因**: プロンプトにDay 0ガイダンスがない
   - **影響**: 非論理的な会話、混乱

#### 高優先度（戦略に影響）

3. **人狼の自己処刑提案** 😵
   - **症状**: ジョナサン（人狼）が自分を処刑提案
   - **原因**: LLMが自分の名前を混同
   - **影響**: 人狼陣営の戦略崩壊

4. **125文字制限で途切れる** ✂️
   - **症状**: 重要な発言が途中で切れる
   - **原因**: LLMが文字数を意識していない
   - **影響**: 情報が不完全

#### 中優先度（改善の余地）

5. **疑惑スコアの差別化不足**
   - 全員5.0点でほぼ差がない
   - 発言内容や投票パターンを反映すべき

6. **早期Over防止機能の動作未確認**
   - 実装済みだがログに出力なし
   - 次回実行で検証必要

---

### 🎯 今後の改善計画

#### 優先度: 🔥 最優先（次回実装）

##### 1. 発言の重複を防止 🔁

**ファイル**: src/agent/seer.py
**症状**: 同じ占い結果を4回報告する
**影響**: 発言枠の無駄遣い

**修正方法**:
```python
class Seer(Agent):
    def __init__(self, ...):
        # ...
        self.reported_results: set[str] = set()  # 報告済み結果を記録

    def create_divine_result_message(self, latest_only: bool = True) -> str:
        if not self.memory.divine_results:
            return ""

        if latest_only:
            result = self.memory.divine_results[-1]
            target = result["target"]
            is_werewolf = result["is_werewolf"]
            day = result["day"]

            # 報告済みかチェック
            result_key = f"{day}_{target}"
            if result_key in self.reported_results:
                return ""

            # まだ報告していない結果のみ（当日の結果）
            if self.info and day == self.info.day:
                self.reported_results.add(result_key)
                if is_werewolf:
                    return f"{target}を占いました。人狼です！投票をお願いします。"
                else:
                    return f"{target}を占いました。村人でした。"
        return ""
```

##### 2. Day 0での幻覚を防止 🤖

**ファイル**: config/config.yml
**症状**: Day 0でまだ起きていないことを話す
**影響**: 非論理的な会話、混乱

**修正方法**:
```yaml
talk: |-
  # 🎯 トークリクエスト（{{ info.day }}日目）

  {% if info.day == 0 -%}
  ## ⚠️ Day 0（初日）の重要な注意
  - **まだ占い結果はありません**（占いは今夜行われます）
  - **まだ夜は来ていません**（夜の行動は話せません）
  - **COするには早すぎます**（情報がまだありません）
  - 一般的な挨拶や、投票先の予想をしてください
  - Day 0では役職を推理するための発言をしましょう

  ## ❌ Day 0で絶対にやってはいけないこと
  - 占い結果の報告（まだ行われていません）
  - 夜の行動の話（まだ夜が来ていません）
  - 役職CO（証拠がありません）
  {%- else -%}
  ## ❌ 禁止事項
  - アリバイや行動説明
  - 一般的な質問や相槌
  {%- endif %}
```

##### 3. 自己処刑防止 😵

**ファイル**: config/config.yml
**症状**: 人狼が自分を処刑提案
**影響**: 陣営戦略の崩壊

**修正方法**:
```yaml
initialize: |-
  # 🎮 人狼ゲーム
  **🔹 あなたの名前**: {{ info.agent }}
  **🔹 あなたの役職**: {{ role.value }}

  ## ⚠️ 絶対に守るべきルール
  - あなたは **{{ info.agent }}** です
  - **絶対に自分自身（{{ info.agent }}）を疑ったり、処刑提案しないこと**
  - これは自殺行為です！
  - 他のプレイヤー: {% for k in info.status_map.keys() %}{% if k != info.agent %}{{ k }} {% endif %}{% endfor %}

talk: |-
  ## 💭 あなたの情報
  - **あなたの名前**: {{ info.agent }}
  - あなたの役職: {{ role.value }}
  - 他のプレイヤー: {% for k in info.status_map.keys() %}{% if k != info.agent %}{{ k }} {% endif %}{% endfor %}

  ## ⚠️ 重要な注意
  - **絶対に自分自身（{{ info.agent }}）を疑わない、処刑提案しない**
```

##### 4. 125文字制限への対応 ✂️

**ファイル**: config/config.yml
**症状**: 発言が途中で切れる
**影響**: 情報が不完全

**修正方法**:
```yaml
talk: |-
  ## ⚡ あなたの発言を生成（**50-115文字厳守**）

  **🚨 重要**: 発言は**115文字以内**に収めてください。
  125文字を超えると途中で切れます！余裕を持って115文字以内にしてください。

  簡潔に、以下のいずれかを含む発言をしてください：
  1. 役職CO（例: 「私は占い師です」）
  2. 占い結果（例: 「〇〇を占った。人狼だ」）
  3. 疑惑の指摘（例: 「〇〇が怪しい。理由は△△」）
  4. 投票提案（例: 「〇〇に投票しよう」）
  5. 議論終了（例: 「Over」）
```

#### 優先度: 🟡 中優先度（次の段階）

##### 5. 疑惑スコア計算の改善

**ファイル**: src/agent/memory.py
**現状**: 全員5.0点でほぼ差がない
**目標**: 発言内容や投票パターンを反映

**改善案**:
- 発言回数が少ない → 疑惑度アップ
- 投票先が人狼と一致 → 疑惑度アップ
- COのタイミングが遅い → 疑惑度アップ
- 矛盾した発言がある → 疑惑度アップ

##### 6. 早期Over防止機能の検証

**ファイル**: src/agent/agent.py
**現状**: 実装済みだがログに出力なし
**必要なアクション**: 次回実行でログを確認

##### 7. プロンプトのさらなる改善

**現状**: 第3フェーズでかなり改善されたが、まだ改善の余地あり

**追加改善案**:
- 役職ごとのより詳細な戦略ガイド
- 過去の会話履歴から推論を促す指示
- 矛盾検出のテンプレート提供

#### 優先度: 🔵 低優先度（将来的に）

##### 8. 人狼・狂人の戦略強化

**目的**: 人狼陣営の勝率を上げる

**実装案**:
- 偽占い師CO機能
- 占い結果の捏造
- 村人陣営の分断戦略
- 真占い師の信用を落とす戦略

**前提条件**: まず占い師が正しく動作することが必須

##### 9. 霊媒師・騎士の実装

**対象**: 13人村に拡張する際
**必要な実装**:
- Medium class の CO機能
- Bodyguard class の護衛戦略
- 霊媒結果と占い結果の整合性チェック

##### 10. パフォーマンス最適化

**改善案**:
- LLMレスポンス時間の短縮
- 会話履歴の要約機能
- キャッシュの活用

---

## 次のアクション

### 🔥 即座に実装すべき項目
1. 発言の重複防止（reported フラグ追加） - seer.py
2. Day 0幻覚防止（プロンプトガイダンス） - config.yml
3. 自己処刑防止（自分の名前を明示） - config.yml
4. 125文字制限対応（文字数警告） - config.yml

### 🧪 実装後の検証
1. 実行テストを行う
2. ログ分析で以下を確認:
   - 占い結果が正しく報告されるか（Enumバグ修正の確認）
   - 発言の重複がなくなったか
   - Day 0での幻覚がなくなったか
   - 自己処刑提案がなくなったか
   - 文字数制限内に収まっているか

### 📈 継続的改善
- 疑惑スコア計算の改善
- プロンプトのさらなる最適化
- 人狼陣営の戦略強化

---


## 開発Tips

### デバッグ方法

#### 1. ログファイルの確認
```bash
# 最新のログディレクトリを確認
ls -lt log/

# 特定のエージェントのログを確認
tail -f log/20260131024524688/kanolab1.log

# エラーを検索
grep "ERROR\|WARNING" log/20260131024524688/*.log
```

#### 2. LLMの応答を確認
ログに以下の形式で記録される:
```
2026-01-31 03:29:02,856 - kanolab1 - INFO - ['LLM', 'プロンプト内容', 'LLMの応答']
```

#### 3. パケットを確認
```
2026-01-31 03:29:02,708 - kanolab1 - DEBUG - Packet(request=<Request.VOTE: 'VOTE'>, ...)
```

### よくある問題

#### 問題: LLMが応答しない
- **原因**: APIキーが未設定、またはレート制限
- **確認**: `config/.env` のAPIキー設定
- **解決**: `llm.sleep_time` を増やす（デフォルト3秒）

#### 問題: タイムアウトエラー
- **原因**: LLMの応答が遅い、または処理が重い
- **確認**: サーバー設定の `timeout.action` (デフォルト60秒)
- **解決**: より高速なモデルを使用、またはタイムアウトを延長

#### 問題: 投票・襲撃が実行されない
- **原因**: 無効なエージェント名を返している
- **確認**: ログで `[Request.VOTE]` の応答を確認
- **解決**: `_parse_agent_name()` が正しく動作しているか確認

### テスト実行

```bash
# サーバー起動（別ターミナル）
cd ../aiwolf-nlp-server
./aiwolf-nlp-server-linux-amd64 -c ./config/default_5.yml

# エージェント起動
cd aiwolf-nlp-agent
python src/main.py -c config/config.yml
```

### 設定のカスタマイズ

#### LLMの変更
```yaml
# OpenAI
llm:
  type: openai

# Google Gemini
llm:
  type: google

# Ollama (ローカル)
llm:
  type: ollama
```

#### ログレベルの変更
```yaml
log:
  level: debug  # debug, info, warning, error
  console_output: true
  file_output: true
```

#### 発言回数の調整
サーバー側で設定:
```yaml
# ../aiwolf-nlp-server/config/default_5.yml
game:
  talk:
    max_count:
      per_agent: 4  # 1人あたりの最大発言数
      per_day: 20   # 1日あたりの全体最大発言数
```

### パフォーマンス改善

1. **LLMのレスポンス時間を短縮**
   - より高速なモデルを使用 (例: gemini-2.0-flash-lite)
   - `temperature` を下げる（0.5-0.7推奨）

2. **不要な会話履歴を削減**
   - 古い会話を要約して保存
   - 重要な情報のみを保持

3. **並列処理の活用**
   - 複数エージェントを並列実行（既に実装済み）

---

## 参考リンク

- **公式サイト**: https://aiwolfdial.github.io/aiwolf-nlp/
- **レギュレーション**: https://aiwolfdial.github.io/aiwolf-nlp/menu/inlg_2025/regulation/
- **エージェント実装ガイド**: https://aiwolfdial.github.io/aiwolf-nlp/menu/inlg_2025/agent/
- **GitHub (Agent)**: https://github.com/aiwolfdial/aiwolf-nlp-agent
- **GitHub (Server)**: https://github.com/aiwolfdial/aiwolf-nlp-server
- **ビューア**: https://github.com/aiwolfdial/aiwolf-nlp-viewer

---

## 更新履歴

- **2026-01-31 (更新3)**: claude.mdを再構成
  - 「完了済みの改善」「実行結果サマリー」「現在の問題点」「今後の改善計画」にセクションを分割
  - 優先度を明確化（最優先/中/低）
  - 次のアクションセクションを追加

- **2026-01-31 (更新2)**: 実行結果を追加、改善案を再整理
  - 第2回実行結果を追加（log/20260131110735209/）
  - 第3回実行結果を追加（log/20260131114137368/）
  - Species型比較バグの完全修正（`.name` 使用）
  - 自己占いバグ修正
  - Day 1 CO戦略実装
  - プロンプト大幅改善

- **2026-01-31 (初版)**: 初版作成
  - ゲームが終了しない問題を解決
  - 応答パース機能を実装
  - プロンプトを改善
  - MemorySystemの実装
  - TalkParserの実装
