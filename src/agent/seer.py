"""Module that defines the Seer agent class.

占い師のエージェントクラスを定義するモジュール.
"""

from __future__ import annotations

from typing import Any

from aiwolf_nlp_common.packet import Role

from agent.agent import Agent


class Seer(Agent):
    """Seer agent class.

    占い師のエージェントクラス.
    """

    def __init__(
        self,
        config: dict[str, Any],
        name: str,
        game_id: str,
        role: Role,  # noqa: ARG002
    ) -> None:
        """Initialize the seer agent.

        占い師のエージェントを初期化する.

        Args:
            config (dict[str, Any]): Configuration dictionary / 設定辞書
            name (str): Agent name / エージェント名
            game_id (str): Game ID / ゲームID
            role (Role): Role (ignored, always set to SEER) / 役職(無視され、常にSEERに設定)
        """
        super().__init__(config, name, game_id, Role.SEER)

        # CO状態管理
        self.has_claimed_seer = False
        self.found_werewolf = False

        # 占った人のリスト（重複占いを避ける）
        self.divined_agents: list[str] = []

    def should_claim_seer(self) -> bool:
        """判断是否应该CO占い師.

        COすべきタイミングかどうかを判断する.

        Returns:
            bool: True if should claim / COすべき場合True
        """
        if self.has_claimed_seer:
            return False

        # 1日目以降、占い結果があれば早期CO（襲撃されるリスクを減らす）
        if self.info and self.info.day >= 1 and self.memory.divine_results:
            return True

        # 人狼を見つけた場合は即CO
        if self.found_werewolf:
            return True

        # 他に占い師COが出た場合は対抗CO
        if self.memory.claims:
            seers = [
                agent for agent, claim in self.memory.claims.items()
                if claim.get("role") == "占い師"
            ]
            if len(seers) > 0:
                return True

        return False

    def create_co_message(self) -> str:
        """占い師COのメッセージを生成する.

        Returns:
            str: CO message / COメッセージ
        """
        message = "私は占い師です。"

        # 占い結果があれば報告
        if self.memory.divine_results:
            message += "これまでの占い結果を報告します。"
            for result in self.memory.divine_results:
                target = result["target"]
                is_werewolf = result["is_werewolf"]
                day = result["day"]

                if is_werewolf:
                    message += f"{day}日目に{target}を占い、人狼でした。"
                else:
                    message += f"{day}日目に{target}を占い、村人でした。"

        return message

    def create_divine_result_message(self, latest_only: bool = True) -> str:
        """占い結果のメッセージを生成する.

        Args:
            latest_only (bool): True if only latest result / 最新の結果のみの場合True

        Returns:
            str: Divine result message / 占い結果メッセージ
        """
        if not self.memory.divine_results:
            return ""

        if latest_only:
            # 最新の結果のみ
            result = self.memory.divine_results[-1]
            target = result["target"]
            is_werewolf = result["is_werewolf"]
            day = result["day"]

            # まだ報告していない結果のみ（当日の結果）
            if self.info and day == self.info.day:
                if is_werewolf:
                    return f"{target}を占いました。人狼です！投票をお願いします。"
                else:
                    return f"{target}を占いました。村人でした。"

        return ""

    def talk(self) -> str:
        """Return response to talk request.

        トークリクエストに対する応答を返す.

        Returns:
            str: Talk message / 発言メッセージ
        """
        # COすべきタイミングかチェック
        if self.should_claim_seer():
            self.has_claimed_seer = True
            co_message = self.create_co_message()
            self.agent_logger.logger.info(f"Claiming SEER: {co_message}")
            return co_message

        # CO済みで、最新の占い結果を報告
        if self.has_claimed_seer:
            result_message = self.create_divine_result_message()
            if result_message:
                self.agent_logger.logger.info(f"Reporting divine result: {result_message}")
                return result_message

        # それ以外は通常の発言
        return super().talk()

    def divine(self) -> str:
        """Return response to divine request.

        占いリクエストに対する応答を返す.

        Returns:
            str: Agent name to divine / 占い対象のエージェント名
        """
        # 生存者を取得
        alive_agents = self.get_alive_agents()

        # 自分の名前を確定（info.agentが最も信頼できる）
        my_name = self.info.agent if self.info else self.agent_name

        # 既に占った人を除外 + 自分自身を除外（重要！）
        candidates = [
            agent for agent in alive_agents
            if agent not in self.divined_agents and agent != my_name
        ]

        if not candidates:
            # 全員占い終わった場合でも自分は除外
            candidates = [a for a in alive_agents if a != my_name]

        # 疑惑度が高い人を優先
        if self.memory.suspicion_scores and candidates:
            candidates_with_score = [
                (agent, self.memory.suspicion_scores.get(agent, 5.0))
                for agent in candidates
            ]
            # 疑惑度が高い順にソート
            candidates_with_score.sort(key=lambda x: x[1], reverse=True)
            target = candidates_with_score[0][0]
        else:
            # スコアがない場合はランダム
            import random
            target = random.choice(candidates)

        # 占った人リストに追加
        self.divined_agents.append(target)

        self.agent_logger.logger.info(f"Divine target: {target}")
        return target

    def daily_initialize(self) -> None:
        """Perform processing for daily initialization request.

        昼開始リクエストに対する処理を行う.
        """
        # 親クラスの処理を実行
        super().daily_initialize()

        # 占い結果をチェック
        if self.info and self.info.divine_result:
            if self.info.divine_result.result.name == "WEREWOLF":  # Enum.name で比較
                self.found_werewolf = True
                self.agent_logger.logger.info(
                    f"Found werewolf: {self.info.divine_result.target}"
                )

    def vote(self) -> str:
        """Return response to vote request.

        投票リクエストに対する応答を返す.

        Returns:
            str: Agent name to vote / 投票対象のエージェント名
        """
        # 人狼を見つけている場合は、その人に投票
        if self.found_werewolf and self.memory.divine_results:
            for result in self.memory.divine_results:
                if result["is_werewolf"]:
                    target = result["target"]
                    # 生存者リストに含まれているかチェック
                    alive_agents = self.get_alive_agents()
                    if target in alive_agents:
                        self.agent_logger.logger.info(
                            f"Voting for confirmed werewolf: {target}"
                        )
                        return target

        # それ以外は親クラスの処理
        return super().vote()
