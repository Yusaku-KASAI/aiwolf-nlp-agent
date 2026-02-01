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

        # 信頼度スコア {agent: score (0.0-10.0)}
        self.trust_scores: dict[str, float] = {}

        # スコアの内訳（分析用）
        self.score_breakdown: dict[str, dict[str, float]] = {}

        # 投票履歴
        self.voting_history: list[dict[str, Any]] = []

        # 占い結果（自分の）
        self.divine_results: list[dict[str, Any]] = []

        # 霊媒結果（自分の）
        self.medium_results: list[dict[str, Any]] = []

        # 発言数カウント
        self.talk_counts: dict[str, int] = {}

        # 現在の日数
        self.current_day: int = 0

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
        """Calculate suspicion score for an agent using multi-factor analysis.

        多要素分析によりエージェントの疑惑スコアを計算する.

        Args:
            agent (str): Target agent / 対象エージェント
            talk_count (int): Number of talks by this agent / このエージェントの発言数
            total_talks (int): Total number of talks / 全体の発言数

        Returns:
            float: Suspicion score (0.0-10.0) / 疑惑スコア
        """
        score = 5.0  # 基本値
        breakdown = {"base": 5.0}

        # 要素1: 矛盾関与度 (Contradiction Involvement)
        contradictions = self.detect_contradictions()
        contradiction_score = 0.0
        for contradiction in contradictions:
            if agent in contradiction.get("agents", []):
                # 矛盾の種類により重み付け
                if contradiction["type"] in ["divine_result_conflict", "medium_result_conflict"]:
                    contradiction_score += 3.0  # 占い/霊媒結果の矛盾は重大
                else:
                    contradiction_score += 2.0  # 複数CO
        breakdown["contradiction"] = contradiction_score
        score += contradiction_score

        # 要素2: 発言頻度 (Talk Frequency)
        talk_score = 0.0
        if total_talks > 0:
            talk_ratio = talk_count / total_talks
            if talk_ratio < 0.05:  # 全体の5%未満（ほぼ沈黙）
                talk_score = 2.5
            elif talk_ratio < 0.15:  # 全体の15%未満（寡黙）
                talk_score = 1.5
            elif talk_ratio < 0.25:  # 全体の25%未満（やや寡黙）
                talk_score = 0.5
        breakdown["talk_frequency"] = talk_score
        score += talk_score

        # 要素3: 投票パターン (Voting Pattern)
        vote_score = 0.0
        agent_votes = [v for v in self.voting_history if v["voter"] == agent]
        if len(agent_votes) > 0:
            # 処刑された人と一致しない投票が多い場合
            mismatched_votes = sum(
                1 for v in agent_votes
                if v["executed"] and v["target"] != v["executed"]
            )
            if len(agent_votes) > 0:
                mismatch_ratio = mismatched_votes / len(agent_votes)
                if mismatch_ratio > 0.6:  # 60%以上が少数派
                    vote_score = 1.5
        breakdown["voting_pattern"] = vote_score
        score += vote_score

        # 要素4: CO遅延 (CO Delay)
        co_score = 0.0
        if self.current_day >= 2:  # 2日目以降
            if agent not in self.claims or "role" not in self.claims[agent]:
                # 役職COをしていない場合、日数に応じて疑惑度を上げる
                co_score = min(2.0, self.current_day * 0.5)
            elif self.claims[agent].get("co_day", 0) > 2:
                # COが遅い場合
                co_score = 1.0
        breakdown["co_delay"] = co_score
        score += co_score

        # 要素5: 役職主張の信頼度 (Claim Credibility)
        credibility_score = 0.0
        if agent in self.claims and "role" in self.claims[agent]:
            role = self.claims[agent]["role"]
            # 占い師COで占い結果が少ない場合
            if role == "占い師":
                divined = self.claims[agent].get("divined", {})
                expected_divines = max(0, self.current_day - self.claims[agent].get("co_day", 0))
                if expected_divines > 0 and len(divined) < expected_divines * 0.5:
                    credibility_score = 1.5  # 占い結果が少なすぎる
        breakdown["claim_credibility"] = credibility_score
        score += credibility_score

        # スコアを0.0-10.0の範囲に収める
        final_score = min(10.0, max(0.0, score))

        # 内訳を保存
        breakdown["total"] = final_score
        self.score_breakdown[agent] = breakdown

        return final_score

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

    def calculate_trust(self, agent: str) -> float:
        """Calculate trust score for an agent based on claim consistency.

        主張の一貫性に基づいてエージェントの信頼度スコアを計算する.

        Args:
            agent (str): Target agent / 対象エージェント

        Returns:
            float: Trust score (0.0-10.0) / 信頼度スコア
        """
        score = 5.0  # 基本値

        # 矛盾に関与していない場合は信頼度アップ
        contradictions = self.detect_contradictions()
        is_involved = any(
            agent in contradiction.get("agents", [])
            for contradiction in contradictions
        )
        if not is_involved:
            score += 2.0

        # 役職COをしている場合
        if agent in self.claims and "role" in self.claims[agent]:
            role = self.claims[agent]["role"]
            co_day = self.claims[agent].get("co_day", 999)

            # 早期COは信頼度アップ（占い師・霊媒師の場合）
            if role in ["占い師", "霊媒師"] and co_day <= 1:
                score += 1.5

            # 占い結果を継続的に報告している場合
            if role == "占い師":
                divined = self.claims[agent].get("divined", {})
                expected_divines = max(0, self.current_day - co_day)
                if expected_divines > 0 and len(divined) >= expected_divines * 0.7:
                    score += 1.5  # 十分な占い結果がある

        # 投票が多数派と一致している場合
        agent_votes = [v for v in self.voting_history if v["voter"] == agent]
        if len(agent_votes) > 0:
            matched_votes = sum(
                1 for v in agent_votes
                if v["executed"] and v["target"] == v["executed"]
            )
            match_ratio = matched_votes / len(agent_votes)
            if match_ratio > 0.5:
                score += 1.0

        # スコアを0.0-10.0の範囲に収める
        return min(10.0, max(0.0, score))

    def calculate_all_trust(self, agents: list[str]) -> dict[str, float]:
        """Calculate trust scores for all agents.

        全エージェントの信頼度スコアを計算する.

        Args:
            agents (list[str]): List of all agents / 全エージェントのリスト

        Returns:
            dict[str, float]: Trust scores / 信頼度スコア
        """
        self.trust_scores = {
            agent: self.calculate_trust(agent) for agent in agents
        }
        return self.trust_scores

    def update_talk_count(self, agent: str, increment: int = 1) -> None:
        """Update talk count for an agent.

        エージェントの発言数を更新する.

        Args:
            agent (str): Agent name / エージェント名
            increment (int): Amount to increment / 増加量
        """
        if agent not in self.talk_counts:
            self.talk_counts[agent] = 0
        self.talk_counts[agent] += increment

    def update_current_day(self, day: int) -> None:
        """Update current day.

        現在の日数を更新する.

        Args:
            day (int): Current day / 現在の日数
        """
        self.current_day = day

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

    def get_most_trustworthy(self, exclude: list[str] | None = None) -> str | None:
        """Get the most trustworthy agent.

        最も信頼できるエージェントを取得する.

        Args:
            exclude (list[str] | None): Agents to exclude / 除外するエージェント

        Returns:
            str | None: Most trustworthy agent or None / 最も信頼できるエージェント
        """
        if not self.trust_scores:
            return None

        exclude = exclude or []
        candidates = {
            agent: score
            for agent, score in self.trust_scores.items()
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
            "trust_scores": self.trust_scores,
            "score_breakdown": self.score_breakdown,
            "talk_counts": self.talk_counts,
            "divine_results_count": len(self.divine_results),
            "medium_results_count": len(self.medium_results),
            "voting_history_count": len(self.voting_history),
            "current_day": self.current_day,
        }

    def get_voting_recommendation(
        self, exclude: list[str] | None = None
    ) -> tuple[str | None, str]:
        """Get voting recommendation with reasoning.

        投票推奨と理由を取得する.

        Args:
            exclude (list[str] | None): Agents to exclude / 除外するエージェント

        Returns:
            tuple[str | None, str]: (recommended agent, reasoning) / (推奨エージェント, 理由)
        """
        if not self.suspicion_scores:
            return None, "疑惑スコアが計算されていません"

        exclude = exclude or []
        candidates = {
            agent: score
            for agent, score in self.suspicion_scores.items()
            if agent not in exclude
        }

        if not candidates:
            return None, "候補者がいません"

        # 最も疑わしいエージェントを選択
        target = max(candidates, key=candidates.get)  # type: ignore
        score = candidates[target]

        # 理由を構築
        reasoning_parts = []
        if target in self.score_breakdown:
            breakdown = self.score_breakdown[target]
            if breakdown.get("contradiction", 0) > 0:
                reasoning_parts.append(
                    f"矛盾関与(+{breakdown['contradiction']:.1f})"
                )
            if breakdown.get("talk_frequency", 0) > 0:
                reasoning_parts.append(
                    f"寡黙(+{breakdown['talk_frequency']:.1f})"
                )
            if breakdown.get("voting_pattern", 0) > 0:
                reasoning_parts.append(
                    f"投票パターン異常(+{breakdown['voting_pattern']:.1f})"
                )
            if breakdown.get("co_delay", 0) > 0:
                reasoning_parts.append(
                    f"CO遅延(+{breakdown['co_delay']:.1f})"
                )
            if breakdown.get("claim_credibility", 0) > 0:
                reasoning_parts.append(
                    f"主張に疑問(+{breakdown['claim_credibility']:.1f})"
                )

        reasoning = f"{target}(疑惑度{score:.1f}): " + ", ".join(reasoning_parts) if reasoning_parts else f"{target}(疑惑度{score:.1f})"

        return target, reasoning
