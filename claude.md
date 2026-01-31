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

### 第1回実行 (log/20260131104130803/)

**実行日**: 2026-01-31
**実装前**: メモリシステム、発言パーサー実装前

#### 発見された問題
1. 占い師が役職COをしない（占い結果も報告なし）
2. 発言が浅く戦略性が低い（すぐに「Over」）
3. 疑惑スコアの差別化が不十分（全員5.0点）
4. 発言パーサーが機能していない

### 第2回実行 (log/20260131110735209/) ⚠️ 最新

**実行日**: 2026-01-31 11:07-11:15
**実装後**: 占い師CO機能、発言品質改善、早期Over防止を実装

#### ゲーム結果
- **占い師**: ミヅキ
- **人狼**: ダイスケ
- **結末**: 人狼陣営の勝利

#### タイムライン
| Day | イベント | 詳細 |
|-----|---------|------|
| 0日目夜 | 占い実行 | ミヅキ→ミヅキを占う（自分自身！） |
| 1日目朝 | 議論 | ミヅキ、CO**せず**（divine_result=None） |
| 1日目夜 | 占い実行 | ミヅキ→ダイスケを占う →**人狼判定** |
| 2日目朝 | 襲撃結果 | ミヅキ（占い師）が**襲撃されて死亡** |
| 2日目 | - | ミヅキは死亡しているため発言不可 |

#### 良い点 ✅
1. ゲームが正常に終了（FINISH受信）
2. メモリシステムが動作
3. 占い結果の記録: `My divine result: ダイスケ -> Species.WEREWOLF` ログ確認
4. 人狼発見検知: `Found werewolf: ダイスケ` ログ確認
5. 早期Over防止機能は動作していない（ログなし）が、実装自体は完了

#### 新たに発見された問題 ⚠️

##### 1. 占い師が自分自身を占ってしまう 🐛 重大
- **症状**: Night 0でミヅキが自分（ミヅキ）を占った
- **ログ証拠**: `['Request.DIVINE', 'ミヅキ']` (11:10:20,457)
- **影響**:
  - Day 1で有効な占い結果がない
  - Day 1でCOできない（divine_resultsが空）
- **原因**: `Seer.divine()` の対象選択ロジックが自分を除外していない

##### 2. 占い結果がメモリに追加されていない 🐛 重大
- **症状**:
  - Day 1: `'divine_results_count': 0`
  - Day 2: `'divine_results_count': 0`
- **ログ証拠**: Memory summary（11:10:20,481、11:13:49,443）
- **影響**:
  - `should_claim_seer()` の条件 `self.memory.divine_results` が常にFalse
  - 占い師が永遠にCOしない
- **原因**:
  - agent.py:366 `self.info.divine_result.result == "WEREWOLF"` がSpecies型と文字列を比較
  - 比較が常にFalseになり、is_werewolf=False で登録される
  - しかしログには `My divine result: ダイスケ -> Species.WEREWOLF` があるので、add_my_divine_result()自体は呼ばれている
  - **Memory summary のログタイミングが早すぎる**: agent.py:357-359でログ、その後363-371でdivine_result追加

##### 3. 占い師が2日目にCOできなかった（死亡のため） 😢
- **症状**: Day 2でミヅキは死亡しているため、TALK要求が来ない
- **ログ証拠**: Day 2のtalk_historyにミヅキの発言なし
- **影響**:
  - 人狼発見（ダイスケ=WEREWOLF）を報告できず
  - 占い師の情報が村人陣営に伝わらない
- **根本原因**:
  - Day 1でCOしなかったため、人狼に狙われやすかった
  - Day 1でCOしない理由は「divine_resultsが空」のため

##### 4. Species型とstring比較のバグ 🐛 クリティカル
- **場所1**: agent.py:366
  ```python
  self.info.divine_result.result == "WEREWOLF"  # Species.WEREWOLF と比較すべき
  ```
- **場所2**: seer.py:204
  ```python
  self.info.divine_result.result == "WEREWOLF"  # 同上
  ```
- **影響**:
  - is_werewolf判定が常にFalseになる
  - found_werewolf フラグがセットされない（実際はログでセットされているが）
- **修正必要**: Species.WEREWOLF または `str(result) == "WEREWOLF"` に変更

##### 5. CO条件が厳しすぎる
- **現在の条件**: `info.day >= 2 and self.memory.divine_results`
- **問題点**:
  - Day 2まで待つと襲撃されるリスクが高い
  - divine_resultsが空だとCOしない
- **提案**: Day 1でもCOする選択肢を追加

#### 結論
実装した機能（占い師CO、早期Over防止）は「コード的には完成」したが、以下の理由で**実際のゲームでは発動しなかった**:
1. 占い師が自分を占う → Day 1で有効な結果なし
2. Memory systemがdivine_resultを正しく追加していない（ログタイミング問題 or Species比較バグ）
3. Day 2の前に占い師が死亡 → CO機能が発動する機会がない

---

## 改善案

### 優先度: 🔥 クリティカル（即修正必須）

これらはゲームを機能不全にする致命的なバグです。

#### 1. Species型とstring比較のバグ修正 🐛

**場所**:
- src/agent/agent.py:366
- src/agent/seer.py:204

**現在のコード**:
```python
# agent.py:366
if self.info and self.info.divine_result:
    self.memory.add_my_divine_result(
        self.info.divine_result.target,
        self.info.divine_result.result == "WEREWOLF",  # ← バグ: Species型とstring比較
        self.info.day,
    )

# seer.py:204
if self.info.divine_result.result == "WEREWOLF":  # ← バグ: Species型とstring比較
    self.found_werewolf = True
```

**修正コード**:
```python
# agent.py:366 - Species型を文字列に変換して比較
if self.info and self.info.divine_result:
    self.memory.add_my_divine_result(
        self.info.divine_result.target,
        str(self.info.divine_result.result) == "WEREWOLF",  # ← 修正
        self.info.day,
    )

# seer.py:204 - 同様に修正
if self.info and self.info.divine_result:
    if str(self.info.divine_result.result) == "WEREWOLF":  # ← 修正
        self.found_werewolf = True
```

**影響**: この修正により占い結果が正しく判定され、人狼発見時にCOが発動するようになる。

#### 2. 占い師が自分自身を占うバグ修正 🐛

**場所**: src/agent/seer.py の `divine()` メソッド

**問題**: 占い対象の選択で自分自身を除外していない

**現在のコード**:
```python
def divine(self) -> str:
    """Return response to divine request."""
    if not self.info:
        return ""

    alive_agents = self.get_alive_agents()
    # 疑惑スコアが高い順にソート
    sorted_agents = sorted(
        alive_agents,
        key=lambda x: self.memory.suspicion_scores.get(x, 5.0),
        reverse=True
    )
    # ... 既に占った人を除外
```

**修正コード**:
```python
def divine(self) -> str:
    """Return response to divine request."""
    if not self.info:
        return ""

    alive_agents = self.get_alive_agents()

    # 自分自身を除外（重要！）
    candidates = [a for a in alive_agents if a != self.name]

    # 既に占った人を除外
    candidates = [a for a in candidates if a not in self.divined_agents]

    if not candidates:
        # 全員占い終わったら、適当に返す
        return alive_agents[0] if alive_agents else ""

    # 疑惑スコアが高い順にソート
    sorted_agents = sorted(
        candidates,
        key=lambda x: self.memory.suspicion_scores.get(x, 5.0),
        reverse=True
    )

    target = sorted_agents[0]
    self.divined_agents.append(target)
    return target
```

**影響**: Night 0で有効な占い結果が得られ、Day 1でCOできるようになる。

### 優先度: ⚠️ 最優先（緊急）

#### 3. 占い師CO条件の改善

**目的**: 占い師が襲撃される前にCOできるようにする

**現状の問題**:
- 現在: `info.day >= 2 and self.memory.divine_results`（2日目までCOしない）
- Day 2まで待つと襲撃されるリスクが高い
- 実際にDay 2の朝には既に死亡していた

**修正案**:
```python
def should_claim_seer(self) -> bool:
    """COすべきタイミングか判断"""
    if self.has_claimed_seer:
        return False

    # Day 1で占い結果があればCO（早期CO戦略）
    if self.info and self.info.day >= 1 and self.memory.divine_results:
        return True

    # 人狼を見つけた場合は即CO
    if self.found_werewolf:
        return True

    # 他に占い師COが出た場合は対抗CO
    if self.memory.claims:
        seers = [agent for agent, claim in self.memory.claims.items()
                if claim.get("role") == "占い師"]
        if len(seers) > 0:
            return True

    return False
```

**メリット**:
- 襲撃されるリスクを減らせる
- 村人陣営に早く情報を伝えられる

**デメリット**:
- 人狼に占い師の位置がバレる
- しかし、黙っていても襲撃されるので、早めにCOする方が得策

---

### 優先度: 🟡 高（できるだけ早く）

これらは既に実装済みだが、上記クリティカルバグのせいで機能していなかった項目です。

#### 4. 占い師CO機能（実装済み、バグ修正後に機能する見込み）

**状態**: ✅ 実装済み (seer.py:128-148)

**既存実装**:
- `should_claim_seer()`: CO判定ロジック
- `create_co_message()`: CO発言生成
- `create_divine_result_message()`: 結果報告生成
- `talk()`: COと結果報告を自動実行

**問題点**: 上記クリティカルバグ(#1, #2)により機能していない

**修正後の動作**:
1. Night 0で他者を占う → Day 1で結果がある
2. Day 1で`should_claim_seer()`がTrueになる
3. Day 1のTALKで自動的にCO

#### 5. 早期Over防止機能（実装済み、テスト不足）

**状態**: ✅ 実装済み (agent.py:216-239)

**既存実装**:
- `my_talk_count_today`: 発言カウンター
- 2回未満の発言でOverを防止
- `_generate_fallback_talk()`: フォールバック発言生成

**問題点**: ログに "Preventing early Over" が出ていない
- LLMが2回以上発言しているためOver防止が発動していない可能性
- または、そもそもLLMが早期にOverを返していない

**要検証**: 次回実行でログを確認

---

### 優先度: 🟢 中（余裕があれば）

#### 6. 発言の質向上 - ゲームの本質に焦点を当てる ⚠️ 重要

**状態**: ⚙️ 一部実装済み（config.yml のプロンプト強化）、但し不十分

**現状の問題**:
ログを見ると、エージェントが**人狼ゲームの本質と無関係な会話**をしている:
- ❌ 「夜道を散歩していた」などのアリバイ会話（意味がない）
- ❌ 「森の入り口付近を歩いていた」などの詳細（ゲームに影響しない）
- ❌ 一般的な質問や相槌（情報が増えない）

**人狼ゲームの本質**:
1. **役職推理**: 誰が占い師か、誰が人狼か
2. **矛盾検出**: 発言内容の矛盾、CO内容の食い違い
3. **勝利戦略**: 自分の陣営が勝つための投票誘導

**改善方針**:
プロンプトに「これは人狼ゲームである」というメタ認知を明示し、本質的な会話に誘導する

**具体的な実装案**:

##### 1. talk プロンプトの抜本的改善
```yaml
talk: |-
  # 🎯 人狼ゲームの本質を理解する
  これは「人狼ゲーム」という推理ゲームです。以下の3点が重要です：
  1. 役職推理: 誰が占い師/人狼/狂人か
  2. 矛盾検出: 発言やCOの矛盾を指摘する
  3. 勝利戦略: 投票で敵陣営を処刑する

  # ❌ やってはいけないこと
  - アリバイや行動の説明（「夜道を散歩していた」など）→ ゲームに影響しない
  - 一般的な質問や相槌 → 情報が増えない
  - 無意味な推測 → 根拠のない発言

  # ✅ やるべきこと
  あなたの役職: {{ role.value }}
  {% if role.value == 'SEER' -%}
  - CO済み？ {{ "はい" if has_claimed_seer else "いいえ" }}
  - 占い結果がある場合は必ず報告
  - 人狼を見つけた場合は投票を呼びかける
  - 他の占い師COがいれば対抗する
  {%- elif role.value == 'WEREWOLF' -%}
  - 村人のふりをする
  - 占い師を特定して襲撃する
  - 偽の推理をして村人を混乱させる
  {%- elif role.value == 'POSSESSED' -%}
  - 村人のふりをする
  - 人狼を守るために誤誘導する
  - 偽占い師COも検討する
  {%- else -%}
  - 占い師のCOを待つ
  - 占い結果を基に人狼を推理する
  - 矛盾する発言をした人を指摘する
  {%- endif %}

  ## 📊 現在の状況（Day {{ info.day }}）
  生存者: {{ status_map.keys() | select("alive") | list | join(", ") }}

  ## 💭 あなたが今すべき発言
  以下のいずれかを含む発言をしてください：
  1. **役職CO**（占い師/霊媒師の場合）
  2. **占い結果の報告**（占い師の場合）
  3. **疑わしい人物の指摘と理由**（過去の発言から）
  4. **投票先の提案と理由**
  5. **他者の発言の矛盾を指摘**

  ## 📜 直近の会話履歴
  {% for w in talk_history[sent_talk_count:] -%}
  {{ w.agent }}: {{ w.text }}
  {% endfor %}

  ## ⚡ あなたの発言を生成してください
  - 文字数: 50-125文字
  - 内容: 上記5つのいずれかに該当する、ゲームの本質に関わる発言
  - 禁止: アリバイ、無意味な質問、一般論
  - 終了: 議論すべき内容がもうない場合のみ「Over」
```

##### 2. initialize プロンプトにゲームの本質を追加
```yaml
initialize: |-
  # 🎮 あなたは人狼ゲームのプレイヤーです

  ## 🎯 ゲームの目的
  これは推理と欺瞞のゲームです。アリバイや一般的な会話は意味がありません。
  重要なのは：役職推理、矛盾検出、投票による処刑です。

  ## あなたの役職と戦略
  {% if role.value == 'SEER' -%}
  【占い師】村人陣営
  - 毎晩1人を占い、人狼か否かを知る
  - Day 1-2で必ずCOする（遅いと襲撃される）
  - 占い結果を村人に共有して人狼を処刑に導く
  {%- elif role.value == 'WEREWOLF' -%}
  【人狼】人狼陣営
  - 占い師を早期に見つけて襲撃する
  - 村人のふりをして疑いを逸らす
  - 偽の推理で村人を混乱させる
  {%- elif role.value == 'POSSESSED' -%}
  【狂人】人狼陣営（占われると村人判定）
  - 人狼を守るために村人を誤誘導する
  - 偽占い師COも有効な戦略
  {%- else -%}
  【村人】村人陣営
  - 占い師のCOと占い結果を信じる
  - 発言の矛盾から人狼を推理する
  - 投票で人狼を処刑する
  {%- endif %}

  ## ⚠️ 重要な注意
  - アリバイや行動説明は不要（ゲームに影響しない）
  - 全ての発言は役職推理か投票誘導に繋がるべき
```

##### 3. daily_initialize プロンプトで前日の分析を促す
```yaml
daily_initialize: |-
  ## 🌅 {{ info.day }}日目の朝が始まりました

  {% if info.executed_agent -%}
  ⚰️ 昨日処刑されたのは: {{ info.executed_agent }}
  {%- endif %}
  {% if info.attacked_agent -%}
  💀 昨晩襲撃されたのは: {{ info.attacked_agent }}
  {%- endif %}

  {% if role.value == 'SEER' and divine_result -%}
  🔍 あなたの占い結果: {{ divine_result.target }} は 【{{ "人狼" if divine_result.result == "WEREWOLF" else "村人" }}】です！
  {%- endif %}

  ## 💭 今日の戦略
  {% if role.value == 'SEER' -%}
  - まだCOしていない場合は今日COする
  - 占い結果を報告する
  - 人狼を見つけた場合は投票を呼びかける
  {%- elif role.value == 'WEREWOLF' -%}
  - 占い師を特定する（COした人を今夜襲撃）
  - 村人のふりを続ける
  {%- elif role.value == 'POSSESSED' -%}
  - 人狼を守るために誤情報を流す
  {%- else -%}
  - 占い師のCOを待つ
  - 占い結果を基に投票先を決める
  {%- endif %}

  現在の生存者: {{ status_map.keys() | select("alive") | list | join(", ") }}
```

#### 7. 疑惑スコア計算の改善

**現状**: 全員5.0点でほぼ差がない

**改善案**:
- 発言内容の感情分析
- 投票パターンの分析
- COのタイミングや内容の矛盾分析
- ただし、現時点では占い師COすら動いていないので、優先度は低い

---

### 優先度: 🔵 低（将来的に）

#### 8. 人狼・狂人の戦略強化

**目的**: 人狼陣営の勝率を上げる

**実装案**:
- 偽占い師CO
- 占い結果の捏造
- 村人陣営の分断戦略

**現状**: 占い師が動いていないので、まず占い師を直してから

#### 9. 霊媒師・騎士の実装

**現状**: 5人村では登場しない

**実装タイミング**: 13人村に拡張する際

---

## TODO（優先順）

1. ✅ **完了**: メモリシステム実装
2. ✅ **完了**: 発言パーサー実装
3. ✅ **完了**: 占い師CO機能実装（コードレベル）
4. ✅ **完了**: 早期Over防止実装
5. 🐛 **今すぐ**: Species型比較バグ修正 (agent.py:366, seer.py:204)
6. 🐛 **今すぐ**: 自分を占うバグ修正 (seer.py divine())
7. ⚠️ **今すぐ**: CO条件を Day 1 に変更 (seer.py should_claim_seer())
8. 🎯 **今すぐ**: プロンプト改善（ゲームの本質に焦点）(config.yml)
9. 🧪 **次**: 実行テスト（上記4点修正後）
10. 📊 **次**: ログ分析（CO機能が実際に動作するか確認）

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
