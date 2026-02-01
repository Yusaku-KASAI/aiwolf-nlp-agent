"""Module for parsing talk messages.

発言を解析するモジュール.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiwolf_nlp_common.packet import Role


class TalkParser:
    """Parser for extracting structured information from talk messages.

    発言から構造化情報を抽出するパーサー.
    """

    # 役職COのパターン
    ROLE_PATTERNS = {
        "占い師": [
            r"(?:私は|僕は|俺は|わたしは)?占い師(?:です|だ|CO|co)",
            r"(?:私が|僕が|俺が|わたしが)?占い(?:です|だ|します|をする)",
            r"占い(?:師)?(?:として)?(?:CO|co)(?:します|する)",
        ],
        "霊媒師": [
            r"(?:私は|僕は|俺は|わたしは)?霊媒師(?:です|だ|CO|co)",
            r"(?:私が|僕が|俺が|わたしが)?霊媒(?:です|だ|します|をする)",
            r"霊媒(?:師)?(?:として)?(?:CO|co)(?:します|する)",
        ],
        "騎士": [
            r"(?:私は|僕は|俺は|わたしは)?騎士(?:です|だ|CO|co)",
            r"(?:私は|僕は|俺は|わたしは)?狩人(?:です|だ|CO|co)",
            r"(?:騎士|狩人)(?:として)?(?:CO|co)(?:します|する)",
        ],
        "村人": [
            r"(?:私は|僕は|俺は|わたしは)?村人(?:です|だ|CO|co)",
            r"村人(?:として)?(?:CO|co)(?:します|する)",
        ],
    }

    def parse_role_claim(self, text: str) -> str | None:
        """Detect role claim (CO).

        役職COを検出する.

        Args:
            text (str): Talk message / 発言メッセージ

        Returns:
            str | None: Claimed role or None / 主張された役職 or None
        """
        for role, patterns in self.ROLE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return role
        return None

    def parse_divine_result(
        self, text: str, agent_names: list[str]
    ) -> dict[str, str] | None:
        """Extract divine result from message.

        発言から占い結果を抽出する.

        Args:
            text (str): Talk message / 発言メッセージ
            agent_names (list[str]): List of agent names / エージェント名のリスト

        Returns:
            dict[str, str] | None: {target: agent, result: "人狼" or "村人"} or None
        """
        for agent in agent_names:
            # パターン1: "Xを占って人狼でした"
            pattern1 = rf"{agent}(?:さん)?(?:を|の)?(?:占って|占い|占った)(?:.*?)(?:人狼|狼|黒)(?:でした|だった|です|判定)"
            if re.search(pattern1, text):
                return {"target": agent, "result": "人狼"}

            # パターン2: "Xは人狼でした"
            pattern2 = (
                rf"{agent}(?:さん)?(?:は|が)(?:.*?)(?:人狼|狼|黒)(?:でした|だった|です)"
            )
            if re.search(pattern2, text):
                return {"target": agent, "result": "人狼"}

            # パターン3: "Xを占って村人でした"
            pattern3 = rf"{agent}(?:さん)?(?:を|の)?(?:占って|占い|占った)(?:.*?)(?:村人|白)(?:でした|だった|です|判定)"
            if re.search(pattern3, text):
                return {"target": agent, "result": "村人"}

            # パターン4: "Xは村人でした"
            pattern4 = (
                rf"{agent}(?:さん)?(?:は|が)(?:.*?)(?:村人|白)(?:でした|だった|です)"
            )
            if re.search(pattern4, text):
                return {"target": agent, "result": "村人"}

            # パターン5: "Xの占い結果は人狼/村人"
            pattern5_wolf = rf"{agent}(?:さん)?(?:の)?(?:占い)?(?:結果)?(?:は|が|:)(?:.*?)(?:人狼|狼|黒)"
            if re.search(pattern5_wolf, text):
                return {"target": agent, "result": "人狼"}

            pattern5_human = rf"{agent}(?:さん)?(?:の)?(?:占い)?(?:結果)?(?:は|が|:)(?:.*?)(?:村人|白)"
            if re.search(pattern5_human, text):
                return {"target": agent, "result": "村人"}

        return None

    def parse_medium_result(
        self, text: str, agent_names: list[str]
    ) -> dict[str, str] | None:
        """Extract medium result from message.

        発言から霊媒結果を抽出する.

        Args:
            text (str): Talk message / 発言メッセージ
            agent_names (list[str]): List of agent names / エージェント名のリスト

        Returns:
            dict[str, str] | None: {target: agent, result: "人狼" or "村人"} or None
        """
        for agent in agent_names:
            # パターン1: "Xを霊媒して人狼でした"
            pattern1 = rf"{agent}(?:さん)?(?:を|の)?(?:霊媒して|霊媒した|霊媒)(?:.*?)(?:人狼|狼|黒)(?:でした|だった|です|判定)"
            if re.search(pattern1, text):
                return {"target": agent, "result": "人狼"}

            # パターン2: "Xは人狼でした（霊媒）"
            pattern2 = (
                rf"{agent}(?:さん)?(?:は|が)(?:.*?)(?:人狼|狼|黒)(?:でした|だった|です)"
            )
            if re.search(pattern2, text) and re.search(r"霊媒", text):
                return {"target": agent, "result": "人狼"}

            # パターン3: "Xを霊媒して村人でした"
            pattern3 = rf"{agent}(?:さん)?(?:を|の)?(?:霊媒して|霊媒した|霊媒)(?:.*?)(?:村人|白)(?:でした|だった|です|判定)"
            if re.search(pattern3, text):
                return {"target": agent, "result": "村人"}

            # パターン4: "Xは村人でした（霊媒）"
            pattern4 = (
                rf"{agent}(?:さん)?(?:は|が)(?:.*?)(?:村人|白)(?:でした|だった|です)"
            )
            if re.search(pattern4, text) and re.search(r"霊媒", text):
                return {"target": agent, "result": "村人"}

            # パターン5: "Xの霊媒結果は人狼/村人"
            pattern5_wolf = rf"{agent}(?:さん)?(?:の)?(?:霊媒)?(?:結果)?(?:は|が|:)(?:.*?)(?:人狼|狼|黒)"
            if re.search(pattern5_wolf, text):
                return {"target": agent, "result": "人狼"}

            pattern5_human = rf"{agent}(?:さん)?(?:の)?(?:霊媒)?(?:結果)?(?:は|が|:)(?:.*?)(?:村人|白)"
            if re.search(pattern5_human, text):
                return {"target": agent, "result": "村人"}

        return None

    def parse_vote_intention(
        self, text: str, agent_names: list[str]
    ) -> str | None:
        """Extract vote intention from message.

        発言から投票意図を抽出する.

        Args:
            text (str): Talk message / 発言メッセージ
            agent_names (list[str]): List of agent names / エージェント名のリスト

        Returns:
            str | None: Target agent or None / 投票対象のエージェント or None
        """
        for agent in agent_names:
            patterns = [
                rf"{agent}(?:さん)?(?:に|へ)(?:投票|入れ)(?:します|する|したい)",
                rf"{agent}(?:さん)?(?:を)?(?:処刑|吊り|吊る)(?:たい|ます|したい)",
                rf"{agent}(?:さん)?(?:に)?(?:票を)?(?:入れ)(?:ます|る)",
            ]
            for pattern in patterns:
                if re.search(pattern, text):
                    return agent
        return None

    def parse_suspicion(self, text: str, agent_names: list[str]) -> str | None:
        """Extract suspicion statement from message.

        発言から疑い発言を抽出する.

        Args:
            text (str): Talk message / 発言メッセージ
            agent_names (list[str]): List of agent names / エージェント名のリスト

        Returns:
            str | None: Suspected agent or None / 疑っているエージェント or None
        """
        for agent in agent_names:
            patterns = [
                rf"{agent}(?:さん)?(?:は|が)?(?:.*?)(?:怪しい|疑わしい|人狼っぽい|狼っぽい|黒い)",
                rf"{agent}(?:さん)?(?:を)?(?:疑って|疑う|疑います|疑っている)",
            ]
            for pattern in patterns:
                if re.search(pattern, text):
                    return agent
        return None

    def parse_defense(self, text: str, agent_names: list[str]) -> str | None:
        """Extract defense statement from message.

        発言から擁護発言を抽出する.

        Args:
            text (str): Talk message / 発言メッセージ
            agent_names (list[str]): List of agent names / エージェント名のリスト

        Returns:
            str | None: Defended agent or None / 擁護しているエージェント or None
        """
        for agent in agent_names:
            patterns = [
                rf"{agent}(?:さん)?(?:は)?(?:.*?)(?:村人|白|信用|味方)",
                rf"{agent}(?:さん)?(?:を)?(?:信じ|信用|擁護)(?:ます|る|している)",
            ]
            for pattern in patterns:
                if re.search(pattern, text):
                    return agent
        return None

    def is_agreement(self, text: str) -> bool:
        """Check if message is an agreement.

        発言が同意かどうかを判定する.

        Args:
            text (str): Talk message / 発言メッセージ

        Returns:
            bool: True if agreement / 同意の場合True
        """
        patterns = [
            r"^(?:同意|賛成|了解|わかりました|承知|そうですね)",
            r"(?:同意します|賛成です|了解です)",
        ]
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        return False

    def is_disagreement(self, text: str) -> bool:
        """Check if message is a disagreement.

        発言が反対かどうかを判定する.

        Args:
            text (str): Talk message / 発言メッセージ

        Returns:
            bool: True if disagreement / 反対の場合True
        """
        patterns = [
            r"^(?:反対|違う|いいえ|待って)",
            r"(?:反対です|違います|そうではない)",
        ]
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        return False

    def extract_all_info(
        self, text: str, agent_names: list[str]
    ) -> dict[str, str | None]:
        """Extract all information from message.

        発言から全ての情報を抽出する.

        Args:
            text (str): Talk message / 発言メッセージ
            agent_names (list[str]): List of agent names / エージェント名のリスト

        Returns:
            dict[str, str | None]: Extracted information / 抽出された情報
        """
        return {
            "role_claim": self.parse_role_claim(text),
            "divine_result": self.parse_divine_result(text, agent_names),
            "medium_result": self.parse_medium_result(text, agent_names),
            "vote_intention": self.parse_vote_intention(text, agent_names),
            "suspicion": self.parse_suspicion(text, agent_names),
            "defense": self.parse_defense(text, agent_names),
            "is_agreement": self.is_agreement(text),
            "is_disagreement": self.is_disagreement(text),
        }
