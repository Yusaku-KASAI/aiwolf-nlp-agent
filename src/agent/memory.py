"""Module for managing agent memory and reasoning.

エージェントの記憶と推論を管理するモジュール.
"""

from __future__ import annotations

from typing import Any


class MemorySystem:
    """Agent memory and reasoning manager.

    エージェントの記憶と推論を管理するクラス.
    """

    def __init__(self) -> None:
        """Initialize memory system.

        記憶システムを初期化する.
        """
        # 役職や占い結果の主張
        # {agent: {role: "占い師", divined: {target: {result: "人狼", day: 1}}}}
        self.claims: dict[str, dict[str, Any]] = {}

        # 検出された矛盾のリスト
        self.contradictions: list[dict[str, Any]] = []

        # 疑惑スコア {agent: score (0.0-10.0)}
        self.suspicion_scores: dict[str, float] = {}

        # 投票履歴
        self.voting_history: list[dict[str, Any]] = []

        # 占い結果（自分の）
        self.divine_results: list[dict[str, Any]] = []

        # 霊媒結果（自分の）
        self.medium_results: list[dict[str, Any]] = []

    def add_role_claim(self, agent: str, role: str, day: int) -> None:
        """Record role claim.

        役職COを記録する.

        Args:
            agent (str): Agent name who claimed / 主張したエージェント名
            role (str): Claimed role / 主張した役職
            day (int): Day of claim / 主張した日
        """
        if agent not in self.claims:
            self.claims[agent] = {}
        self.claims[agent]["role"] = role
        self.claims[agent]["co_day"] = day

    def add_divine_claim(
        self, agent: str, target: str, result: str, day: int
    ) -> None:
        """Record divine result claim.

        占い結果の主張を記録する.

        Args:
            agent (str): Agent who claimed divine result / 占い結果を主張したエージェント
            target (str): Target of divine / 占い対象
            result (str): Divine result (人狼 or 村人) / 占い結果
            day (int): Day of claim / 主張した日
        """
        if agent not in self.claims:
            self.claims[agent] = {}
        if "divined" not in self.claims[agent]:
            self.claims[agent]["divined"] = {}
        self.claims[agent]["divined"][target] = {"result": result, "day": day}

    def add_medium_claim(
        self, agent: str, target: str, result: str, day: int
    ) -> None:
        """Record medium result claim.

        霊媒結果の主張を記録する.

        Args:
            agent (str): Agent who claimed medium result / 霊媒結果を主張したエージェント
            target (str): Target of medium / 霊媒対象
            result (str): Medium result (人狼 or 村人) / 霊媒結果
            day (int): Day of claim / 主張した日
        """
        if agent not in self.claims:
            self.claims[agent] = {}
        if "mediumed" not in self.claims[agent]:
            self.claims[agent]["mediumed"] = {}
        self.claims[agent]["mediumed"][target] = {"result": result, "day": day}

    def add_vote(
        self, voter: str, target: str, day: int, executed: str | None = None
    ) -> None:
        """Record voting.

        投票を記録する.

        Args:
            voter (str): Agent who voted / 投票したエージェント
            target (str): Target of vote / 投票対象
            day (int): Day of vote / 投票した日
            executed (str | None): Executed agent if any / 処刑されたエージェント（いる場合）
        """
        self.voting_history.append(
            {"voter": voter, "target": target, "day": day, "executed": executed}
        )

    def add_my_divine_result(
        self, target: str, is_werewolf: bool, day: int
    ) -> None:
        """Record my own divine result.

        自分の占い結果を記録する.

        Args:
            target (str): Target of divine / 占い対象
            is_werewolf (bool): Whether target is werewolf / 対象が人狼か
            day (int): Day of divine / 占った日
        """
        self.divine_results.append(
            {"target": target, "is_werewolf": is_werewolf, "day": day}
        )

    def add_my_medium_result(
        self, target: str, is_werewolf: bool, day: int
    ) -> None:
        """Record my own medium result.

        自分の霊媒結果を記録する.

        Args:
            target (str): Target of medium / 霊媒対象
            is_werewolf (bool): Whether target was werewolf / 対象が人狼だったか
            day (int): Day of medium / 霊媒した日
        """
        self.medium_results.append(
            {"target": target, "is_werewolf": is_werewolf, "day": day}
        )

    def detect_contradictions(self) -> list[dict[str, Any]]:
        """Detect contradictions in claims.

        主張の中から矛盾を検出する.

        Returns:
            list[dict[str, Any]]: List of detected contradictions / 検出された矛盾のリスト
        """
        contradictions: list[dict[str, Any]] = []

        # 複数の占い師COをチェック
        seers = [
            agent
            for agent, claim in self.claims.items()
            if claim.get("role") == "占い師"
        ]
        if len(seers) > 1:
            contradictions.append(
                {
                    "type": "multiple_seers",
                    "agents": seers,
                    "description": f"複数の占い師が存在: {', '.join(seers)}",
                }
            )

        # 複数の霊媒師COをチェック
        mediums = [
            agent
            for agent, claim in self.claims.items()
            if claim.get("role") == "霊媒師"
        ]
        if len(mediums) > 1:
            contradictions.append(
                {
                    "type": "multiple_mediums",
                    "agents": mediums,
                    "description": f"複数の霊媒師が存在: {', '.join(mediums)}",
                }
            )

        # 占い結果の矛盾をチェック
        for i, agent1 in enumerate(seers):
            for agent2 in seers[i + 1 :]:
                divined1 = self.claims[agent1].get("divined", {})
                divined2 = self.claims[agent2].get("divined", {})
                common_targets = set(divined1.keys()) & set(divined2.keys())
                for target in common_targets:
                    if divined1[target]["result"] != divined2[target]["result"]:
                        contradictions.append(
                            {
                                "type": "divine_result_conflict",
                                "agents": [agent1, agent2],
                                "target": target,
                                "results": {
                                    agent1: divined1[target]["result"],
                                    agent2: divined2[target]["result"],
                                },
                                "description": (
                                    f"{agent1}と{agent2}の{target}への占い結果が矛盾"
                                ),
                            }
                        )

        # 霊媒結果の矛盾をチェック
        for i, agent1 in enumerate(mediums):
            for agent2 in mediums[i + 1 :]:
                mediumed1 = self.claims[agent1].get("mediumed", {})
                mediumed2 = self.claims[agent2].get("mediumed", {})
                common_targets = set(mediumed1.keys()) & set(mediumed2.keys())
                for target in common_targets:
                    if mediumed1[target]["result"] != mediumed2[target]["result"]:
                        contradictions.append(
                            {
                                "type": "medium_result_conflict",
                                "agents": [agent1, agent2],
                                "target": target,
                                "results": {
                                    agent1: mediumed1[target]["result"],
                                    agent2: mediumed2[target]["result"],
                                },
                                "description": (
                                    f"{agent1}と{agent2}の{target}への霊媒結果が矛盾"
                                ),
                            }
                        )

        self.contradictions = contradictions
        return contradictions

    def calculate_suspicion(
        self, agent: str, talk_count: int = 0, total_talks: int = 1
    ) -> float:
        """Calculate suspicion score for an agent.

        エージェントの疑惑スコアを計算する.

        Args:
            agent (str): Target agent / 対象エージェント
            talk_count (int): Number of talks by this agent / このエージェントの発言数
            total_talks (int): Total number of talks / 全体の発言数

        Returns:
            float: Suspicion score (0.0-10.0) / 疑惑スコア
        """
        score = 5.0  # 基本値

        # 矛盾に関与している場合
        contradictions = self.detect_contradictions()
        for contradiction in contradictions:
            if agent in contradiction.get("agents", []):
                score += 2.5

        # 発言が少ない場合（寡黙は疑わしい）
        if total_talks > 0:
            talk_ratio = talk_count / total_talks
            if talk_ratio < 0.1:  # 全体の10%未満の発言
                score += 1.0

        # 役職COをしていない場合（後半で）
        if agent not in self.claims or "role" not in self.claims[agent]:
            # 日数に応じて疑惑度を上げる（後で実装）
            pass

        # スコアを0.0-10.0の範囲に収める
        return min(10.0, max(0.0, score))

    def calculate_all_suspicions(
        self, agents: list[str], talk_counts: dict[str, int] | None = None
    ) -> dict[str, float]:
        """Calculate suspicion scores for all agents.

        全エージェントの疑惑スコアを計算する.

        Args:
            agents (list[str]): List of all agents / 全エージェントのリスト
            talk_counts (dict[str, int] | None): Talk counts by agent / エージェントごとの発言数

        Returns:
            dict[str, float]: Suspicion scores / 疑惑スコア
        """
        if talk_counts is None:
            talk_counts = {}

        total_talks = sum(talk_counts.values())

        self.suspicion_scores = {
            agent: self.calculate_suspicion(
                agent, talk_counts.get(agent, 0), total_talks
            )
            for agent in agents
        }

        return self.suspicion_scores

    def get_most_suspicious(self, exclude: list[str] | None = None) -> str | None:
        """Get the most suspicious agent.

        最も疑わしいエージェントを取得する.

        Args:
            exclude (list[str] | None): Agents to exclude / 除外するエージェント

        Returns:
            str | None: Most suspicious agent or None / 最も疑わしいエージェント
        """
        if not self.suspicion_scores:
            return None

        exclude = exclude or []
        candidates = {
            agent: score
            for agent, score in self.suspicion_scores.items()
            if agent not in exclude
        }

        if not candidates:
            return None

        return max(candidates, key=candidates.get)  # type: ignore

    def get_summary(self) -> dict[str, Any]:
        """Get summary of memory system.

        記憶システムのサマリーを取得する.

        Returns:
            dict[str, Any]: Summary / サマリー
        """
        return {
            "claims": self.claims,
            "contradictions": self.contradictions,
            "suspicion_scores": self.suspicion_scores,
            "divine_results_count": len(self.divine_results),
            "medium_results_count": len(self.medium_results),
            "voting_history_count": len(self.voting_history),
        }
