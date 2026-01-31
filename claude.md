# AIWolf NLP Agent - Claude開発者用ドキュメント

## 目次
1. [プロジェクト概要](#プロジェクト概要)
2. [人狼ゲームのルール](#人狼ゲームのルール)
3. [システムアーキテクチャ](#システムアーキテクチャ)
4. [エージェント実装](#エージェント実装)
5. [判明した問題と解決策](#判明した問題と解決策)
6. [改善案](#改善案)
7. [開発Tips](#開発tips)

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

### 問題1: ゲームが終了しない ⚠️ 重大

#### 症状
- 11日目まで進行しても終了しない
- 5人全員が生存している
- 投票・襲撃が実行されない (executed_agent=None, attacked_agent=None)

#### 原因
LLMが不適切な応答を返し、それをそのままサーバーに送信していた。

**ログの証拠**:
```
[Request.VOTE] → LLM返答: "投票結果を共有してください。"  ❌
[Request.ATTACK] → LLM返答: "襲撃を開始します。"  ❌
```

期待される応答: `"シュンイチ"`, `"アスカ"` などのエージェント名のみ

#### 根本原因
1. **応答の検証なし**: `vote()`, `attack()`, `divine()`, `guard()` がLLMの応答をそのまま返す
2. **パース処理なし**: エージェント名のリストとの照合なし
3. **プロンプトが不明確**: LLMが説明文を返してしまう

#### 解決策（実装済み）

##### 1. 応答パース機能を追加 (`src/agent/agent.py`)
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

##### 2. プロンプトの改善 (`config/config.yml`)
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

#### 動作の変更
- **修正前**: `"投票結果を共有してください。"` → そのまま送信 → 無効
- **修正後**: `"投票結果を共有してください。"` → 警告ログ + ランダム選択 → 有効なエージェント名を送信

---

## 改善案

### 優先度: 高

#### 1. 記憶・推論システムの実装

**目的**: 過去の発言や行動を構造化して記憶し、論理的推論に活用

**実装案**:
```python
# src/agent/memory.py (新規作成)
class MemorySystem:
    """エージェントの記憶と推論を管理"""

    def __init__(self):
        self.claims = {}  # {agent: {role: "占い師", divined: {target: result}}}
        self.contradictions = []  # 矛盾リスト
        self.suspicion_scores = {}  # {agent: suspicion_score}
        self.voting_history = []  # 投票パターン
        self.divine_results = []  # 占い結果

    def add_role_claim(self, agent: str, role: str, day: int):
        """役職COを記録"""
        if agent not in self.claims:
            self.claims[agent] = {}
        self.claims[agent]["role"] = role
        self.claims[agent]["co_day"] = day

    def add_divine_claim(self, agent: str, target: str, result: str, day: int):
        """占い結果の主張を記録"""
        if agent not in self.claims:
            self.claims[agent] = {}
        if "divined" not in self.claims[agent]:
            self.claims[agent]["divined"] = {}
        self.claims[agent]["divined"][target] = {"result": result, "day": day}

    def detect_contradictions(self) -> list[dict]:
        """矛盾を検出"""
        contradictions = []

        # 複数の占い師COをチェック
        seers = [a for a, c in self.claims.items() if c.get("role") == "占い師"]
        if len(seers) > 1:
            contradictions.append({
                "type": "multiple_seers",
                "agents": seers,
                "description": "複数の占い師が存在"
            })

        # 占い結果の矛盾をチェック
        for agent1 in seers:
            for agent2 in seers:
                if agent1 >= agent2:
                    continue
                divined1 = self.claims[agent1].get("divined", {})
                divined2 = self.claims[agent2].get("divined", {})
                common_targets = set(divined1.keys()) & set(divined2.keys())
                for target in common_targets:
                    if divined1[target]["result"] != divined2[target]["result"]:
                        contradictions.append({
                            "type": "divine_result_conflict",
                            "agents": [agent1, agent2],
                            "target": target,
                            "results": [divined1[target], divined2[target]]
                        })

        return contradictions

    def calculate_suspicion(self, agent: str) -> float:
        """疑わしさスコアを計算 (0.0-10.0)"""
        score = 5.0  # 基本値

        # 矛盾に関与している場合
        contradictions = self.detect_contradictions()
        for c in contradictions:
            if agent in c.get("agents", []):
                score += 2.0

        # 発言が少ない場合
        # TODO: 発言数を追跡して評価

        return min(10.0, max(0.0, score))
```

**プロンプトへの統合**:
```yaml
talk: |-
  ## あなたの役職と目標
  役職: {{ role.value }}

  ## 疑わしいプレイヤー
  {% if suspicion_scores -%}
  {% for agent, score in suspicion_scores.items() -%}
  {{ agent }}: 疑惑度 {{ score }}/10
  {% endfor %}
  {%- endif %}

  ## 検出された矛盾
  {% if contradictions -%}
  {% for c in contradictions -%}
  - {{ c.description }}
  {% endfor %}
  {%- endif %}
```

#### 2. 発言パーサーの実装

**目的**: 他のエージェントの発言から構造化情報を自動抽出

**実装案**:
```python
# src/utils/talk_parser.py (新規作成)
import re
from typing import Optional
from aiwolf_nlp_common.packet import Role

class TalkParser:
    """発言から構造化情報を抽出"""

    # 役職COのパターン
    ROLE_PATTERNS = {
        Role.SEER: [
            r"(?:私は|僕は|俺は)?占い師(?:です|だ|CO)",
            r"(?:私が|僕が|俺が)?占い(?:です|だ|します)",
        ],
        Role.MEDIUM: [
            r"(?:私は|僕は|俺は)?霊媒師(?:です|だ|CO)",
            r"(?:私が|僕が|俺が)?霊媒(?:です|だ|します)",
        ],
        Role.BODYGUARD: [
            r"(?:私は|僕は|俺は)?騎士(?:です|だ|CO)",
            r"(?:私は|僕は|俺は)?狩人(?:です|だ|CO)",
        ],
    }

    def parse_role_claim(self, text: str) -> Optional[Role]:
        """役職COを検出"""
        for role, patterns in self.ROLE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return role
        return None

    def parse_divine_result(self, text: str, agent_names: list[str]) -> Optional[dict]:
        """占い結果を抽出

        例: "アスカを占って人狼でした" → {target: "アスカ", result: "人狼"}
        """
        for agent in agent_names:
            # パターン1: "Xを占って人狼でした"
            pattern1 = rf"{agent}(?:さん)?を?(?:占って|占い)(?:.*?)(?:人狼|狼|黒)(?:でした|だった)"
            if re.search(pattern1, text):
                return {"target": agent, "result": "人狼"}

            # パターン2: "Xは人狼でした"
            pattern2 = rf"{agent}(?:さん)?は(?:.*?)(?:人狼|狼|黒)(?:でした|だった|です)"
            if re.search(pattern2, text):
                return {"target": agent, "result": "人狼"}

            # パターン3: "Xを占って村人でした"
            pattern3 = rf"{agent}(?:さん)?を?(?:占って|占い)(?:.*?)(?:村人|白)(?:でした|だった)"
            if re.search(pattern3, text):
                return {"target": agent, "result": "村人"}

            # パターン4: "Xは村人でした"
            pattern4 = rf"{agent}(?:さん)?は(?:.*?)(?:村人|白)(?:でした|だった|です)"
            if re.search(pattern4, text):
                return {"target": agent, "result": "村人"}

        return None

    def parse_vote_intention(self, text: str, agent_names: list[str]) -> Optional[str]:
        """投票意図を抽出

        例: "アスカに投票します" → "アスカ"
        """
        for agent in agent_names:
            patterns = [
                rf"{agent}(?:さん)?(?:に|へ)(?:投票|入れ)(?:します|する)",
                rf"{agent}(?:さん)?(?:を)?(?:処刑|吊り)(?:たい|ます)",
            ]
            for pattern in patterns:
                if re.search(pattern, text):
                    return agent
        return None
```

**Agentクラスへの統合**:
```python
class Agent:
    def __init__(self, ...):
        ...
        self.memory = MemorySystem()
        self.parser = TalkParser()

    def daily_initialize(self):
        """朝の初期化時に発言を解析"""
        if self.talk_history:
            for talk in self.talk_history:
                # 役職COを検出
                role = self.parser.parse_role_claim(talk.text)
                if role:
                    self.memory.add_role_claim(talk.agent, role, self.info.day)

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
```

### 優先度: 中

#### 3. 役職別戦略の実装

**現状**: 役職別クラスは親クラスを呼ぶだけ

**改善案**:

```python
# src/agent/seer.py
class Seer(Agent):
    """占い師エージェント"""

    def __init__(self, config, name, game_id, role):
        super().__init__(config, name, game_id, Role.SEER)
        self.divine_results = []  # 占い結果履歴
        self.has_claimed_seer = False  # CO済みか
        self.found_werewolf = False  # 人狼発見済みか

    def divine(self) -> str:
        """戦略的な占い先選択"""
        alive_agents = self.get_alive_agents()

        # 既に占った人を除外
        divined = [r["target"] for r in self.divine_results]
        candidates = [a for a in alive_agents if a not in divined and a != self.agent_name]

        if not candidates:
            return random.choice(alive_agents)

        # 疑惑度が高い人を優先
        if self.memory.suspicion_scores:
            candidates_with_score = [
                (agent, self.memory.suspicion_scores.get(agent, 5.0))
                for agent in candidates
            ]
            # 疑惑度が高い順にソート
            candidates_with_score.sort(key=lambda x: x[1], reverse=True)
            return candidates_with_score[0][0]

        return random.choice(candidates)

    def talk(self) -> str:
        """戦略的な発言"""
        # COすべきか判断
        if not self.has_claimed_seer and self.should_claim_seer():
            self.has_claimed_seer = True
            return self.create_seer_co_message()

        # 占い結果を共有
        if self.has_claimed_seer and self.divine_results:
            latest = self.divine_results[-1]
            if latest["day"] == self.info.day and not latest.get("announced", False):
                latest["announced"] = True
                return self.create_divine_result_message(latest)

        return super().talk()

    def should_claim_seer(self) -> bool:
        """COすべきタイミングか判断"""
        # 人狼を見つけた場合は即CO
        if self.found_werewolf:
            return True

        # 他に占い師COが出た場合
        contradictions = self.memory.detect_contradictions()
        for c in contradictions:
            if c["type"] == "multiple_seers":
                return True

        # 3日目以降は基本的にCO
        if self.info.day >= 3:
            return True

        return False

    def create_seer_co_message(self) -> str:
        """占い師CO発言を生成"""
        msg = "私は占い師です。"
        if self.divine_results:
            msg += f"これまでの占い結果を報告します。"
        return msg

    def create_divine_result_message(self, result: dict) -> str:
        """占い結果発言を生成"""
        target = result["target"]
        is_werewolf = result["result"]
        if is_werewolf:
            return f"{target}を占いました。人狼です。"
        else:
            return f"{target}を占いました。村人です。"

    def daily_initialize(self):
        """朝の初期化"""
        super().daily_initialize()

        # 占い結果を記録
        if self.info.divine_result:
            self.divine_results.append({
                "day": self.info.day,
                "target": self.info.divine_result.target,
                "result": self.info.divine_result.result == "WEREWOLF",
            })
            if self.info.divine_result.result == "WEREWOLF":
                self.found_werewolf = True
```

#### 4. Chain-of-Thought プロンプト

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

#### 5. 多様なLLMモデルの活用

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

- **2026-01-31**: 初版作成
  - ゲームが終了しない問題を解決
  - 応答パース機能を実装
  - プロンプトを改善
  - 改善案を追加

---

## TODO

- [ ] MemorySystemの実装
- [ ] TalkParserの実装
- [ ] 役職別戦略の実装（Seer, Werewolf）
- [ ] Chain-of-Thoughtプロンプトの実装
- [ ] ユニットテストの追加
- [ ] 勝率の測定と分析
