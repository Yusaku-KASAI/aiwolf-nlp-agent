# AIWolf NLP Agent - Claude開発者用ドキュメント

## 目次
1. [プロジェクト概要](#プロジェクト概要)
2. [人狼ゲームのルール](#人狼ゲームのルール)
3. [システムアーキテクチャ](#システムアーキテクチャ)
4. [エージェント実装](#エージェント実装)
5. [判明した問題と解決策](#判明した問題と解決策)
6. [実行結果と新たな問題点](#実行結果と新たな問題点)
7. [改善案](#改善案)
8. [開発Tips](#開発tips)

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

## 判明した問題と解決策

### 完了済みの改善（2026-01-31実装）

#### 問題1: ゲームが終了しない ⚠️ 重大（解決済み）

##### 症状
- 11日目まで進行しても終了しない
- 5人全員が生存している
- 投票・襲撃が実行されない (executed_agent=None, attacked_agent=None)

##### 原因
LLMが不適切な応答を返し、それをそのままサーバーに送信していた。

**ログの証拠**:
```
[Request.VOTE] → LLM返答: "投票結果を共有してください。"  ❌
[Request.ATTACK] → LLM返答: "襲撃を開始します。"  ❌
```

期待される応答: `"シュンイチ"`, `"アスカ"` などのエージェント名のみ

##### 根本原因
1. **応答の検証なし**: `vote()`, `attack()`, `divine()`, `guard()` がLLMの応答をそのまま返す
2. **パース処理なし**: エージェント名のリストとの照合なし
3. **プロンプトが不明確**: LLMが説明文を返してしまう

##### 解決策（実装済み）

###### 1. 応答パース機能を追加 (`src/agent/agent.py`)
```python
def _parse_agent_name(self, response: str | None) -> str:
    """LLMの応答からエージェント名を抽出・検証する"""
    if not response:
        self.agent_logger.logger.warning("LLM returned empty response. Using random agent.")
        return random.choice(self.get_alive_agents())

    # 空白と句読点を除去
    cleaned = response.strip().rstrip("。、.,!！?？")

    # 生存エージェントのリストを取得
    alive_agents = self.get_alive_agents()

    # 完全一致を確認
    if cleaned in alive_agents:
        return cleaned

    # 応答の中にエージェント名が含まれているか確認
    for agent in alive_agents:
        if agent in response:
            self.agent_logger.logger.info(
                f"Extracted agent name '{agent}' from response: {response}"
            )
            return agent

    # 無効な応答の場合はランダム選択
    self.agent_logger.logger.warning(
        f"Invalid agent name in response: '{response}'. Using random choice."
    )
    return random.choice(alive_agents)
```

###### 2. プロンプトの改善 (`config/config.yml`)
```yaml
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

同様の改善を `divine`, `guard`, `attack` にも適用。

##### 動作の変更
- **修正前**: `"投票結果を共有してください。"` → そのまま送信 → 無効
- **修正後**: `"投票結果を共有してください。"` → 警告ログ + ランダム選択 → 有効なエージェント名を送信

#### 問題2: 記憶・推論システムの欠如（解決済み）

##### 症状
- 過去の発言や行動が記憶されない
- 論理的推論ができない
- 矛盾を検出できない

##### 解決策（実装済み）
`src/agent/memory.py` に記憶・推論システムを実装。
- 役職COの記録
- 占い結果の記録
- 矛盾検出
- 疑惑スコア計算

#### 問題3: 発言パーサーの欠如（解決済み）

##### 症状
- 他のエージェントの発言から情報を抽出できない
- 役職COや占い結果を認識できない

##### 解決策（実装済み）
`src/utils/talk_parser.py` に発言パーサーを実装。
- 役職COの検出
- 占い結果の抽出
- 投票意図の抽出

---

## 実行結果と新たな問題点

**実行日**: 2026-01-31
**ログ**: log/20260131104130803/

### 良い点
- ゲームが正常に終了（FINISHリクエスト受信）
- メモリシステムが動作（Memory summary記録）
- 疑惑スコアが計算される
- 投票・襲撃が正常に機能

### 新たに発見された問題

#### 1. 占い師が役職COをしない ⚠️ 重大
- **症状**: 占い師（ミオ）が自分の役職を公表していない
- **影響**: 占い結果も報告していない
- **ログ確認**: claimsが常に空{}
- **原因分析**:
  - `should_claim_seer()` の条件が厳しすぎる可能性
  - LLMが占い師COの発言を生成していない
  - プロンプトに占い師COの指示が不足

#### 2. 発言が浅く戦略性が低い
- **症状**:
  - すぐに「Over」を言ってしまう
  - 情報収集や推論が不足
  - 一般的な会話のみで、役職に関する議論がない
- **原因分析**:
  - プロンプトが具体的な行動を促していない
  - LLMが人狼ゲームの戦略を理解していない
  - 会話を継続するインセンティブがない

#### 3. 疑惑スコアの差別化が不十分
- **症状**: ほぼ全員が5.0点
- **影響**: 行動や発言内容が反映されていない
- **原因分析**:
  - スコア計算ロジックが単純すぎる
  - 発言内容の分析が不足
  - 投票パターンが考慮されていない

#### 4. 発言パーサーが実質機能していない
- **症状**: 役職COや占い結果を報告する発言自体がない
- **影響**: パーサーのテストができていない
- **原因分析**:
  - そもそも発言生成側が役職COをしていない
  - パーサーの実装は正しいが、テストデータがない

---

## 改善案

### 優先度: 最優先（緊急）

#### 1. 占い師の役職CO機能の修正 ⚠️

**目的**: 占い師が適切なタイミングで役職COし、占い結果を報告できるようにする

**現状の問題**:
- 占い師（Seer）が自分の役職を公表していない
- 占い結果も報告していない
- ログでclaimsが常に空{}

**実装案**:

##### 1. `src/agent/seer.py` の `should_claim_seer()` を修正
```python
def should_claim_seer(self) -> bool:
    """COすべきタイミングか判断"""
    # 1日目の夜に占い結果があれば、2日目にCO
    if self.info.day >= 2 and not self.has_claimed_seer:
        return True

    # 人狼を見つけた場合は即CO
    if self.found_werewolf:
        return True

    # 他に占い師COが出た場合
    seers = [a for a, c in self.memory.claims.items() if c.get("role") == "占い師"]
    if len(seers) > 0:
        return True

    return False
```

##### 2. プロンプトに占い師CO指示を追加
```yaml
# config/config.yml の seer 用 talk プロンプト
seer_talk: |-
  あなたは占い師です。以下のガイドラインに従って発言してください：

  1. まだ役職COしていない場合、「私は占い師です」と明確に宣言する
  2. 占い結果がある場合、「[名前]を占いました。[結果]です」と報告する
  3. 人狼を見つけた場合は強く主張し、投票を呼びかける

  現在の状況：
  - 日数: {{ info.day }}日目
  - 占い済み: {% for r in divine_results %}{{ r.target }}({{ "人狼" if r.result else "村人" }}){% if not loop.last %}, {% endif %}{% endfor %}
  - CO済み: {{ "はい" if has_claimed_seer else "いいえ" }}
```

##### 3. `talk()` メソッドを修正して確実にCOさせる
```python
def talk(self) -> str:
    """戦略的な発言"""
    # 最優先: COすべきか判断
    if not self.has_claimed_seer and self.should_claim_seer():
        self.has_claimed_seer = True
        message = self.create_seer_co_message()
        self.agent_logger.logger.info(f"Claiming seer role: {message}")
        return message

    # 占い結果の報告（CO済みの場合のみ）
    if self.has_claimed_seer and self.divine_results:
        latest = self.divine_results[-1]
        if latest["day"] == self.info.day and not latest.get("announced", False):
            latest["announced"] = True
            message = self.create_divine_result_message(latest)
            self.agent_logger.logger.info(f"Announcing divine result: {message}")
            return message

    # 通常の発言
    return super().talk()

def create_seer_co_message(self) -> str:
    """占い師CO発言を生成（LLMに頼らず確実に生成）"""
    return "私は占い師です。"

def create_divine_result_message(self, result: dict) -> str:
    """占い結果発言を生成（LLMに頼らず確実に生成）"""
    target = result["target"]
    is_werewolf = result["result"]
    if is_werewolf:
        return f"{target}を占いました。人狼です。投票をお願いします。"
    else:
        return f"{target}を占いました。村人です。"
```

#### 2. 発言の質と量を改善

**目的**: 浅い発言や即「Over」を防ぎ、戦略的な会話を促進

**実装案**:

##### 1. プロンプトに具体的な指示を追加
```yaml
talk: |-
  ## あなたの役割
  役職: {{ role.value }}
  目標: {{ "人狼を見つけて処刑する" if role.value in ["村人", "占い師", "霊媒師", "騎士"] else "村人を混乱させて生き残る" }}

  ## 発言ガイドライン
  以下のいずれかの内容を含む発言をしてください（複数可）：
  1. 疑わしいプレイヤーの指摘と理由
  2. 他のプレイヤーの発言への質問や反論
  3. 自分の考えや推論の共有
  4. 投票先の提案と理由
  5. 役職COがある場合の検証や議論

  ## 重要
  - 「Over」は最後の手段です。まだ議論すべきことがある場合は発言を続けてください
  - 発言は50文字以上、125文字以内を推奨
  - 具体的な名前や理由を含めてください

  ## 会話履歴
  {% for w in talk_history[sent_talk_count:] -%}
  {{ w.agent }}: {{ w.text }}
  {% endfor %}

  ## あなたの発言
  上記を踏まえて、戦略的な発言をしてください。
  議論すべき内容がもうない場合のみ「Over」と発言してください。
```

##### 2. 発言数カウンターの実装
```python
class Agent:
    def __init__(self, ...):
        ...
        self.talk_count_today = 0
        self.max_talk_per_day = 4

    def talk(self) -> str:
        """発言生成"""
        self.talk_count_today += 1

        # 最後の発言機会の場合は必ず内容のある発言をする
        if self.talk_count_today >= self.max_talk_per_day:
            response = self._send_message_to_llm_with_instruction(
                "これが最後の発言機会です。重要な情報や意見を必ず述べてください。"
            )
            return response if response and response != "Over" else self._generate_fallback_talk()

        return super().talk()

    def _generate_fallback_talk(self) -> str:
        """LLMが適切な応答をしない場合のフォールバック発言"""
        alive = self.get_alive_agents()
        if len(alive) > 1:
            # 疑惑スコアが高い人を指摘
            if self.memory.suspicion_scores:
                top_suspect = max(
                    self.memory.suspicion_scores.items(),
                    key=lambda x: x[1]
                )
                return f"{top_suspect[0]}の発言が気になります。"
        return "引き続き様子を見ます。"
```

### 優先度: 高

#### 3. 疑惑スコアの計算ロジック改善

**目的**: 発言内容や行動パターンを反映した精度の高いスコアを算出

**実装案**:

##### 1. `src/agent/memory.py` の `calculate_suspicion()` を拡張
```python
def calculate_suspicion(self, agent: str, info) -> float:
    """疑わしさスコアを計算 (0.0-10.0)"""
    score = 5.0  # 基本値

    # 1. 矛盾に関与している場合 (+2.0点)
    contradictions = self.detect_contradictions()
    for c in contradictions:
        if agent in c.get("agents", []):
            score += 2.0

    # 2. 発言が少ない場合 (+1.0点)
    if agent in self.talk_counts:
        if self.talk_counts[agent] < 2:
            score += 1.0

    # 3. 「Over」が多い場合 (+0.5点)
    if agent in self.over_counts:
        if self.over_counts[agent] > 2:
            score += 0.5

    # 4. 占い結果が黒の場合 (+3.0点)
    for claimer, claim_data in self.claims.items():
        divined = claim_data.get("divined", {})
        if agent in divined:
            if divined[agent]["result"] == "人狼":
                score += 3.0

    # 5. 投票パターンが不自然（吊られた人に投票していない）(-1.0点)
    if self.voting_history:
        for vote_record in self.voting_history:
            if vote_record["executed"]:
                if agent in vote_record["votes"]:
                    if vote_record["votes"][agent] != vote_record["executed"]:
                        score += 0.5

    # 6. 生存日数が長い（最終日に近い場合）(+0.5点)
    if info.day >= 4:
        score += 0.5

    return min(10.0, max(0.0, score))
```

##### 2. 発言カウント機能の追加
```python
class MemorySystem:
    def __init__(self):
        ...
        self.talk_counts = {}  # {agent: count}
        self.over_counts = {}  # {agent: over_count}

    def record_talk(self, agent: str, text: str):
        """発言を記録"""
        if agent not in self.talk_counts:
            self.talk_counts[agent] = 0
        self.talk_counts[agent] += 1

        if text.strip() == "Over":
            if agent not in self.over_counts:
                self.over_counts[agent] = 0
            self.over_counts[agent] += 1

    def record_vote(self, day: int, votes: dict, executed: str):
        """投票結果を記録"""
        self.voting_history.append({
            "day": day,
            "votes": votes,
            "executed": executed
        })
```

#### 4. 発言パーサーのテストと検証

**目的**: パーサーが正しく動作していることを確認

**実装案**:

##### 1. ユニットテストの追加 (`tests/test_talk_parser.py`)
```python
import pytest
from src.utils.talk_parser import TalkParser
from aiwolf_nlp_common.packet import Role

def test_parse_role_claim_seer():
    parser = TalkParser()

    # 占い師COのパターン
    assert parser.parse_role_claim("私は占い師です") == Role.SEER
    assert parser.parse_role_claim("占い師CO") == Role.SEER
    assert parser.parse_role_claim("僕が占いします") == Role.SEER

def test_parse_divine_result():
    parser = TalkParser()
    agents = ["アスカ", "ミオ", "シュンイチ"]

    # 人狼判定
    result = parser.parse_divine_result("アスカを占って人狼でした", agents)
    assert result == {"target": "アスカ", "result": "人狼"}

    # 村人判定
    result = parser.parse_divine_result("ミオを占って村人でした", agents)
    assert result == {"target": "ミオ", "result": "村人"}

def test_parse_vote_intention():
    parser = TalkParser()
    agents = ["アスカ", "ミオ", "シュンイチ"]

    # 投票意図
    assert parser.parse_vote_intention("アスカに投票します", agents) == "アスカ"
    assert parser.parse_vote_intention("ミオを処刑したい", agents) == "ミオ"
```

##### 2. デバッグログの追加
```python
# src/agent/agent.py
def daily_initialize(self):
    """朝の初期化時に発言を解析"""
    if self.talk_history:
        for talk in self.talk_history:
            # 発言カウント
            self.memory.record_talk(talk.agent, talk.text)

            # 役職COを検出
            role = self.parser.parse_role_claim(talk.text)
            if role:
                self.memory.add_role_claim(talk.agent, role.value, self.info.day)
                self.agent_logger.logger.info(
                    f"Detected role claim: {talk.agent} -> {role.value}"
                )

            # 占い結果を検出
            alive_agents = self.get_alive_agents()
            divine_result = self.parser.parse_divine_result(talk.text, alive_agents)
            if divine_result:
                self.memory.add_divine_claim(
                    talk.agent,
                    divine_result["target"],
                    divine_result["result"],
                    self.info.day
                )
                self.agent_logger.logger.info(
                    f"Detected divine result: {talk.agent} -> {divine_result}"
                )

        # メモリの状態をログに出力
        self.agent_logger.logger.info(f"Memory claims: {self.memory.claims}")
        self.agent_logger.logger.info(f"Talk counts: {self.memory.talk_counts}")
```

### 優先度: 中

#### 5. 記憶・推論システムの継続的改善（実装済みのため拡張）

**目的**: 既に実装された記憶システムをさらに拡張

**実装案**（既存のMemorySystemクラス）:
    """エージェントの記憶と推論を管理"""
    # 実装済み - さらなる拡張として以下を追加

    def analyze_voting_patterns(self, agent: str) -> dict:
        """投票パターンを分析"""
        patterns = {
            "always_follows_majority": False,
            "protects_specific_agent": None,
            "voting_consistency": 0.0
        }

        if not self.voting_history:
            return patterns

        # 多数派に従うかチェック
        follow_count = 0
        for vote_record in self.voting_history:
            if agent in vote_record["votes"]:
                voted_for = vote_record["votes"][agent]
                # 最終的に処刑された人に投票していたか
                if voted_for == vote_record.get("executed"):
                    follow_count += 1

        if len(self.voting_history) > 0:
            patterns["voting_consistency"] = follow_count / len(self.voting_history)

        return patterns

    def get_memory_summary(self) -> str:
        """記憶の要約を生成（プロンプトへの埋め込み用）"""
        summary = []

        # 役職CO情報
        if self.claims:
            summary.append("【役職CO情報】")
            for agent, claim in self.claims.items():
                if "role" in claim:
                    summary.append(f"- {agent}: {claim['role']} (CO日: {claim['co_day']}日目)")

        # 占い結果情報
        for agent, claim in self.claims.items():
            if "divined" in claim:
                summary.append(f"\n【{agent}の占い結果】")
                for target, result in claim["divined"].items():
                    summary.append(f"- {target}: {result['result']} ({result['day']}日目)")

        # 矛盾情報
        contradictions = self.detect_contradictions()
        if contradictions:
            summary.append("\n【検出された矛盾】")
            for c in contradictions:
                summary.append(f"- {c['description']}")

        return "\n".join(summary) if summary else "特記事項なし"
```

**プロンプトへの統合例**:
```yaml
talk: |-
  ## 記憶情報
  {{ memory_summary }}

  ## 疑惑度ランキング
  {% if suspicion_scores -%}
  {% for agent, score in suspicion_scores.items() | sort(attribute='1', reverse=True) -%}
  {{ loop.index }}. {{ agent }}: {{ "%.1f"|format(score) }}/10
  {% endfor %}
  {%- endif %}
```

#### 6. 役職別戦略の拡張（実装済みのため追加機能）

**実装済みの拡張**: 占い師以外の役職にも戦略を追加

```python
# src/agent/werewolf.py
class Werewolf(Agent):
    """人狼エージェント"""

    def __init__(self, config, name, game_id, role):
        super().__init__(config, name, game_id, Role.WEREWOLF)
        self.fake_seer_claim = False  # 偽占い師CO済みか
        self.fake_divine_results = []  # 偽占い結果

    def talk(self) -> str:
        """人狼の戦略的な発言"""
        # 真の占い師が出た場合、対抗COを検討
        seers = [a for a, c in self.memory.claims.items() if c.get("role") == "占い師"]
        if len(seers) > 0 and not self.fake_seer_claim and self.info.day >= 2:
            # 対抗COする
            self.fake_seer_claim = True
            return "私も占い師です。真実を明らかにします。"

        # 偽占い結果を報告
        if self.fake_seer_claim and self.should_announce_fake_result():
            return self.create_fake_divine_result()

        return super().talk()

    def should_announce_fake_result(self) -> bool:
        """偽占い結果を報告すべきか"""
        # まだ報告していない占い結果がある場合
        return len(self.fake_divine_results) < self.info.day - 1

    def create_fake_divine_result(self) -> str:
        """偽の占い結果を生成（村人を白判定）"""
        alive = self.get_alive_agents()
        # 自分と他の人狼を除外
        candidates = [a for a in alive if a != self.agent_name]
        if candidates:
            target = random.choice(candidates)
            self.fake_divine_results.append({"target": target, "result": "村人"})
            return f"{target}を占いました。村人です。"
        return "Over"

    def attack(self) -> str:
        """襲撃先を決定（真の占い師を優先）"""
        alive_agents = self.get_alive_agents()

        # 真の占い師を優先的に襲撃
        seers = [a for a, c in self.memory.claims.items()
                 if c.get("role") == "占い師" and a != self.agent_name and a in alive_agents]

        if seers:
            # 複数いる場合は最初にCOした人を襲撃
            seers_sorted = sorted(seers, key=lambda a: self.memory.claims[a].get("co_day", 99))
            return seers_sorted[0]

        # 占い師がいない場合は疑惑度が低い人を襲撃（ステルス対策）
        if self.memory.suspicion_scores:
            candidates_with_score = [
                (agent, self.memory.suspicion_scores.get(agent, 5.0))
                for agent in alive_agents if agent != self.agent_name
            ]
            # 疑惑度が低い順にソート
            candidates_with_score.sort(key=lambda x: x[1])
            return candidates_with_score[0][0]

        return self._parse_agent_name(super().attack())
```

```python
# src/agent/villager.py
class Villager(Agent):
    """村人エージェント"""

    def vote(self) -> str:
        """投票先を決定（疑惑度を考慮）"""
        # 疑惑度が最も高い人に投票
        if self.memory.suspicion_scores:
            alive = self.get_alive_agents()
            alive_scores = {
                agent: self.memory.suspicion_scores.get(agent, 5.0)
                for agent in alive if agent != self.agent_name
            }
            if alive_scores:
                top_suspect = max(alive_scores.items(), key=lambda x: x[1])
                self.agent_logger.logger.info(
                    f"Voting for top suspect: {top_suspect[0]} (score: {top_suspect[1]})"
                )
                return top_suspect[0]

        return self._parse_agent_name(super().vote())
```

#### 7. Chain-of-Thought プロンプト

**目的**: LLMに思考過程を踏ませて推論精度を向上

**実装案**:
```yaml
vote: |-
  ## ステップ1: 状況整理
  現在{{ info.day }}日目です。生存者は以下の通りです：
  {% for k, v in info.status_map.items() -%}
  {%- if v == 'ALIVE' -%}
  - {{ k }}
  {% endif -%}
  {%- endfor %}

  ## ステップ2: 各プレイヤーの評価
  各プレイヤーについて、人狼である可能性を評価してください。
  考慮すべき点：
  - 発言内容の一貫性
  - 占い結果との整合性
  - 投票行動のパターン
  - 疑わしい発言や行動

  ## ステップ3: 最終決定
  最も人狼である可能性が高いプレイヤーの名前のみを出力してください。
  説明は不要です。名前だけを出力してください。

  対象:
  {% for k, v in info.status_map.items() -%}
  {%- if v == 'ALIVE' -%}
  {{ k }}
  {% endif -%}
  {%- endfor %}
```

### 優先度: 低

#### 8. 多様なLLMモデルの活用

**アイデア**: 重要な判断には強力なモデルを使用

```python
def vote(self) -> str:
    """投票は重要なので強力なモデルを使用"""
    if self.config["llm"].get("use_strong_model_for_vote", False):
        original_model = self.llm_model
        self.llm_model = self.create_model("gpt-4")
        response = self._send_message_to_llm(self.request)
        self.llm_model = original_model
    else:
        response = self._send_message_to_llm(self.request)
    return self._parse_agent_name(response)
```

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

- **2026-01-31 (更新2)**: 実行結果を追加、改善案を再整理
  - 実行結果セクションを追加（log/20260131104130803/）
  - 新たな問題点を4つ発見
    1. 占い師が役職COをしない（重大）
    2. 発言が浅く戦略性が低い
    3. 疑惑スコアの差別化が不十分
    4. 発言パーサーが実質機能していない
  - 改善案の優先度を再編成（最優先/高/中/低）
  - 完了済みの改善を明確化

- **2026-01-31 (初版)**: 初版作成
  - ゲームが終了しない問題を解決
  - 応答パース機能を実装
  - プロンプトを改善
  - MemorySystemの実装
  - TalkParserの実装
  - 改善案を追加

---

## TODO

### 最優先
- [ ] 占い師の役職CO機能を修正（should_claim_seerの条件緩和）
- [ ] 占い師COメッセージを確実に生成（LLMに頼らない）
- [ ] 占い師用プロンプトの追加
- [ ] 発言の質と量を改善（具体的な指示をプロンプトに追加）
- [ ] フォールバック発言機能の実装

### 高優先度
- [ ] 疑惑スコアの計算ロジック拡張（発言数、投票パターンを考慮）
- [ ] 発言カウント機能の追加
- [ ] 発言パーサーのユニットテスト作成
- [ ] デバッグログの強化（パーサー検出結果の出力）

### 中優先度
- [ ] MemorySystemの拡張（投票パターン分析、記憶要約）
- [ ] 人狼の戦略実装（偽占い師CO、襲撃戦略）
- [ ] 村人の投票戦略実装（疑惑度ベース）
- [ ] Chain-of-Thoughtプロンプトの実装

### 低優先度
- [ ] 多様なLLMモデルの活用（重要判断に強力モデル）
- [ ] 勝率の測定と分析
- [ ] パフォーマンスの最適化
