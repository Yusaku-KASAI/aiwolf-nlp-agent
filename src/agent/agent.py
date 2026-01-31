"""Module that defines the base class for agents.

エージェントの基底クラスを定義するモジュール.
"""

from __future__ import annotations

import os
import random
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

from dotenv import load_dotenv
from jinja2 import Template
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import BaseMessage

from aiwolf_nlp_common.packet import Info, Packet, Request, Role, Setting, Status, Talk

from agent.memory import MemorySystem
from utils.agent_logger import AgentLogger
from utils.stoppable_thread import StoppableThread
from utils.talk_parser import TalkParser

if TYPE_CHECKING:
    from collections.abc import Callable

P = ParamSpec("P")
T = TypeVar("T")


class Agent:
    """Base class for agents.

    エージェントの基底クラス.
    """

    def __init__(
        self,
        config: dict[str, Any],
        name: str,
        game_id: str,
        role: Role,
    ) -> None:
        """Initialize the agent.

        エージェントの初期化を行う.

        Args:
            config (dict[str, Any]): Configuration dictionary / 設定辞書
            name (str): Agent name / エージェント名
            game_id (str): Game ID / ゲームID
            role (Role): Role / 役職
        """
        self.config = config
        self.agent_name = name
        self.agent_logger = AgentLogger(config, name, game_id)
        self.request: Request | None = None
        self.info: Info | None = None
        self.setting: Setting | None = None
        self.talk_history: list[Talk] = []
        self.whisper_history: list[Talk] = []
        self.role = role

        self.sent_talk_count: int = 0
        self.sent_whisper_count: int = 0
        self.llm_model: BaseChatModel | None = None
        self.llm_message_history: list[BaseMessage] = []

        # Memory and reasoning system
        # 記憶・推論システム
        self.memory = MemorySystem()
        self.parser = TalkParser()

        # Talk counts for suspicion calculation
        # 疑惑度計算用の発言数
        self.talk_counts: dict[str, int] = {}

        # Own talk count in current day
        # 今日の自分の発言回数
        self.my_talk_count_today: int = 0

        load_dotenv(Path(__file__).parent.joinpath("./../../config/.env"))

    @staticmethod
    def timeout(func: Callable[P, T]) -> Callable[P, T]:
        """Decorator to set action timeout.

        アクションタイムアウトを設定するデコレータ.

        Args:
            func (Callable[P, T]): Function to be decorated / デコレート対象の関数

        Returns:
            Callable[P, T]: Function with timeout functionality / タイムアウト機能を追加した関数
        """

        def _wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            res: T | Exception = Exception("No result")

            def execute_with_timeout() -> None:
                nonlocal res
                try:
                    res = func(*args, **kwargs)
                except Exception as e:  # noqa: BLE001
                    res = e

            thread = StoppableThread(target=execute_with_timeout)
            thread.start()
            self = args[0] if args else None
            if not isinstance(self, Agent):
                raise TypeError(self, " is not an Agent instance")
            timeout_value = (
                self.setting.timeout.action
                if hasattr(self, "setting") and self.setting
                else 0
            ) // 1000
            if timeout_value > 0:
                thread.join(timeout=timeout_value)
                if thread.is_alive():
                    self.agent_logger.logger.warning(
                        "アクションがタイムアウトしました: %s",
                        self.request,
                    )
                    if bool(self.config["agent"]["kill_on_timeout"]):
                        thread.stop()
                        self.agent_logger.logger.warning(
                            "アクションを強制終了しました: %s",
                            self.request,
                        )
            else:
                thread.join()
            if isinstance(res, Exception):  # type: ignore[arg-type]
                raise res
            return res

        return _wrapper

    def set_packet(self, packet: Packet) -> None:
        """Set packet information.

        パケット情報をセットする.

        Args:
            packet (Packet): Received packet / 受信したパケット
        """
        self.request = packet.request
        if packet.info:
            self.info = packet.info
        if packet.setting:
            self.setting = packet.setting
        if packet.talk_history:
            self.talk_history.extend(packet.talk_history)
        if packet.whisper_history:
            self.whisper_history.extend(packet.whisper_history)
        if self.request == Request.INITIALIZE:
            self.talk_history: list[Talk] = []
            self.whisper_history: list[Talk] = []
            self.llm_message_history: list[BaseMessage] = []
        self.agent_logger.logger.debug(packet)

    def get_alive_agents(self) -> list[str]:
        """Get the list of alive agents.

        生存しているエージェントのリストを取得する.

        Returns:
            list[str]: List of alive agent names / 生存エージェント名のリスト
        """
        if not self.info:
            return []
        return [k for k, v in self.info.status_map.items() if v == Status.ALIVE]

    def _send_message_to_llm(self, request: Request | None) -> str | None:
        """Send message to LLM and get response.

        LLMにメッセージを送信して応答を取得する.

        Args:
            request (Request | None): The request type to process / 処理するリクエストタイプ

        Returns:
            str | None: LLM response or None if error occurred / LLMの応答またはエラー時はNone
        """
        if request is None:
            return None
        if request.lower() not in self.config["prompt"]:
            return None
        prompt = self.config["prompt"][request.lower()]
        if float(self.config["llm"]["sleep_time"]) > 0:
            sleep(float(self.config["llm"]["sleep_time"]))
        key = {
            "info": self.info,
            "setting": self.setting,
            "talk_history": self.talk_history,
            "whisper_history": self.whisper_history,
            "role": self.role,
            "sent_talk_count": self.sent_talk_count,
            "sent_whisper_count": self.sent_whisper_count,
            # Memory system data
            # 記憶システムのデータ
            "suspicion_scores": self.memory.suspicion_scores,
            "contradictions": self.memory.contradictions,
            "claims": self.memory.claims,
            "divine_results": self.memory.divine_results,
            "medium_results": self.memory.medium_results,
        }
        template: Template = Template(prompt)
        prompt = template.render(**key).strip()
        if self.llm_model is None:
            self.agent_logger.logger.error("LLM is not initialized")
            return None
        try:
            self.llm_message_history.append(HumanMessage(content=prompt))
            response = (self.llm_model | StrOutputParser()).invoke(
                self.llm_message_history
            )
            self.llm_message_history.append(AIMessage(content=response))
            self.agent_logger.logger.info(["LLM", prompt, response])
        except Exception:
            self.agent_logger.logger.exception("Failed to send message to LLM")
            return None
        else:
            return response

    @timeout
    def name(self) -> str:
        """Return response to name request.

        名前リクエストに対する応答を返す.

        Returns:
            str: Agent name / エージェント名
        """
        return self.agent_name

    def initialize(self) -> None:
        """Perform initialization for game start request.

        ゲーム開始リクエストに対する初期化処理を行う.
        """
        if self.info is None:
            return

        model_type = str(self.config["llm"]["type"])
        match model_type:
            case "openai":
                self.llm_model = ChatOpenAI(
                    model=str(self.config["openai"]["model"]),
                    temperature=float(self.config["openai"]["temperature"]),
                    api_key=SecretStr(os.environ["OPENAI_API_KEY"]),
                )
            case "google":
                self.llm_model = ChatGoogleGenerativeAI(
                    model=str(self.config["google"]["model"]),
                    temperature=float(self.config["google"]["temperature"]),
                    api_key=SecretStr(os.environ["GOOGLE_API_KEY"]),
                )
            case "ollama":
                self.llm_model = ChatOllama(
                    model=str(self.config["ollama"]["model"]),
                    temperature=float(self.config["ollama"]["temperature"]),
                    base_url=str(self.config["ollama"]["base_url"]),
                )
            case "dmr":
                self.llm_model = ChatOpenAI(
                    model=str(self.config["dmr"]["model"]),
                    temperature=float(self.config["dmr"]["temperature"]),
                    api_key=SecretStr("dummy"),
                    base_url=str(self.config["dmr"]["base_url"]),
                )
            case _:
                raise ValueError(model_type, "Unknown LLM type")
        self.llm_model = self.llm_model
        self._send_message_to_llm(self.request)

    def daily_initialize(self) -> None:
        """Perform processing for daily initialization request.

        昼開始リクエストに対する処理を行う.
        """
        # Reset daily talk count
        # 1日の発言回数をリセット
        self.my_talk_count_today = 0

        # Parse talk history and update memory
        # 発言履歴を解析してメモリを更新
        if self.talk_history:
            alive_agents = self.get_alive_agents()

            # Count talks by each agent
            # 各エージェントの発言数をカウント
            for talk in self.talk_history:
                self.talk_counts[talk.agent] = self.talk_counts.get(talk.agent, 0) + 1

                # Parse talk content
                # 発言内容を解析
                info = self.parser.extract_all_info(talk.text, alive_agents)

                # Record role claim
                # 役職COを記録
                if info["role_claim"]:
                    self.memory.add_role_claim(
                        talk.agent, info["role_claim"], self.info.day if self.info else 0
                    )
                    self.agent_logger.logger.info(
                        f"Role claim detected: {talk.agent} -> {info['role_claim']}"
                    )

                # Record divine result claim
                # 占い結果の主張を記録
                if info["divine_result"]:
                    result = info["divine_result"]
                    self.memory.add_divine_claim(
                        talk.agent,
                        result["target"],
                        result["result"],
                        self.info.day if self.info else 0,
                    )
                    self.agent_logger.logger.info(
                        f"Divine result detected: {talk.agent} -> {result['target']}: {result['result']}"
                    )

                # Record medium result claim
                # 霊媒結果の主張を記録
                if info["medium_result"]:
                    result = info["medium_result"]
                    self.memory.add_medium_claim(
                        talk.agent,
                        result["target"],
                        result["result"],
                        self.info.day if self.info else 0,
                    )
                    self.agent_logger.logger.info(
                        f"Medium result detected: {talk.agent} -> {result['target']}: {result['result']}"
                    )

            # Detect contradictions
            # 矛盾を検出
            contradictions = self.memory.detect_contradictions()
            if contradictions:
                self.agent_logger.logger.info(f"Contradictions detected: {contradictions}")

            # Calculate suspicion scores
            # 疑惑スコアを計算
            self.memory.calculate_all_suspicions(alive_agents, self.talk_counts)

            self.agent_logger.logger.debug(
                f"Memory summary: {self.memory.get_summary()}"
            )

        # Record my divine result if available
        # 自分の占い結果を記録
        if self.info and self.info.divine_result:
            self.memory.add_my_divine_result(
                self.info.divine_result.target,
                self.info.divine_result.result.name == "WEREWOLF",  # Enum.name で比較
                self.info.day,
            )
            self.agent_logger.logger.info(
                f"My divine result: {self.info.divine_result.target} -> {self.info.divine_result.result} (is_werewolf={self.info.divine_result.result.name == 'WEREWOLF'})"
            )

        # Record my medium result if available
        # 自分の霊媒結果を記録
        if self.info and self.info.medium_result:
            self.memory.add_my_medium_result(
                self.info.medium_result.target,
                self.info.medium_result.result.name == "WEREWOLF",  # Enum.name で比較
                self.info.day,
            )
            self.agent_logger.logger.info(
                f"My medium result: {self.info.medium_result.target} -> {self.info.medium_result.result}"
            )

        self._send_message_to_llm(self.request)

    def whisper(self) -> str:
        """Return response to whisper request.

        囁きリクエストに対する応答を返す.

        Returns:
            str: Whisper message / 囁きメッセージ
        """
        response = self._send_message_to_llm(self.request)
        self.sent_whisper_count = len(self.whisper_history)
        return response or ""

    def talk(self) -> str:
        """Return response to talk request.

        トークリクエストに対する応答を返す.

        Returns:
            str: Talk message / 発言メッセージ
        """
        response = self._send_message_to_llm(self.request)
        self.sent_talk_count = len(self.talk_history)

        # Early Over prevention
        # 早期Over防止
        if response and response.strip() == "Over":
            # 今日まだ2回未満しか発言していない場合は、Overを防止
            if self.my_talk_count_today < 2:
                self.agent_logger.logger.info(
                    f"Preventing early Over (talk count: {self.my_talk_count_today})"
                )
                # フォールバック発言を生成
                response = self._generate_fallback_talk()

        # 発言回数をカウント
        if response and response.strip() != "Over":
            self.my_talk_count_today += 1

        return response or ""

    def _generate_fallback_talk(self) -> str:
        """Generate fallback talk when preventing early Over.

        早期Overを防止する際のフォールバック発言を生成する.

        Returns:
            str: Fallback talk message / フォールバック発言
        """
        # 役職に応じたフォールバック発言
        if self.role == Role.SEER:
            return "状況を整理したいと思います。皆さんの意見を聞かせてください。"
        elif self.role == Role.WEREWOLF:
            return "もう少し情報を集めたいですね。"
        elif self.role == Role.POSSESSED:
            return "慎重に判断したいので、もう少し議論しましょう。"
        else:  # VILLAGER, MEDIUM, BODYGUARD
            return "皆さんの意見を参考にしたいです。"

    def daily_finish(self) -> None:
        """Perform processing for daily finish request.

        昼終了リクエストに対する処理を行う.
        """
        self._send_message_to_llm(self.request)

    def _parse_agent_name(self, response: str | None) -> str:
        """Parse and validate agent name from LLM response.

        LLMの応答からエージェント名を抽出・検証する.

        Args:
            response (str | None): LLM response / LLMの応答

        Returns:
            str: Valid agent name / 有効なエージェント名
        """
        if not response:
            self.agent_logger.logger.warning("LLM returned empty response. Using random agent.")
            return random.choice(self.get_alive_agents())  # noqa: S311

        # Strip whitespace and common punctuation
        # 空白と句読点を除去
        cleaned = response.strip().rstrip("。、.,!！?？")

        # Get list of alive agents
        # 生存エージェントのリストを取得
        alive_agents = self.get_alive_agents()

        # Check for exact match
        # 完全一致を確認
        if cleaned in alive_agents:
            return cleaned

        # Check if any agent name is contained in the response
        # 応答の中にエージェント名が含まれているか確認
        for agent in alive_agents:
            if agent in response:
                self.agent_logger.logger.info(
                    f"Extracted agent name '{agent}' from response: {response}"
                )
                return agent

        # No valid agent name found, use random choice
        # 有効なエージェント名が見つからない場合はランダム選択
        self.agent_logger.logger.warning(
            f"Invalid agent name in response: '{response}'. Using random choice."
        )
        return random.choice(alive_agents)  # noqa: S311

    def divine(self) -> str:
        """Return response to divine request.

        占いリクエストに対する応答を返す.

        Returns:
            str: Agent name to divine / 占い対象のエージェント名
        """
        response = self._send_message_to_llm(self.request)
        return self._parse_agent_name(response)

    def guard(self) -> str:
        """Return response to guard request.

        護衛リクエストに対する応答を返す.

        Returns:
            str: Agent name to guard / 護衛対象のエージェント名
        """
        response = self._send_message_to_llm(self.request)
        return self._parse_agent_name(response)

    def vote(self) -> str:
        """Return response to vote request.

        投票リクエストに対する応答を返す.

        Returns:
            str: Agent name to vote / 投票対象のエージェント名
        """
        response = self._send_message_to_llm(self.request)
        return self._parse_agent_name(response)

    def attack(self) -> str:
        """Return response to attack request.

        襲撃リクエストに対する応答を返す.

        Returns:
            str: Agent name to attack / 襲撃対象のエージェント名
        """
        response = self._send_message_to_llm(self.request)
        return self._parse_agent_name(response)

    def finish(self) -> None:
        """Perform processing for game finish request.

        ゲーム終了リクエストに対する処理を行う.
        """

    @timeout
    def action(self) -> str | None:  # noqa: C901, PLR0911
        """Execute action according to request type.

        リクエストの種類に応じたアクションを実行する.

        Returns:
            str | None: Action result string or None / アクションの結果文字列またはNone
        """
        match self.request:
            case Request.NAME:
                return self.name()
            case Request.TALK:
                return self.talk()
            case Request.WHISPER:
                return self.whisper()
            case Request.VOTE:
                return self.vote()
            case Request.DIVINE:
                return self.divine()
            case Request.GUARD:
                return self.guard()
            case Request.ATTACK:
                return self.attack()
            case Request.INITIALIZE:
                self.initialize()
            case Request.DAILY_INITIALIZE:
                self.daily_initialize()
            case Request.DAILY_FINISH:
                self.daily_finish()
            case Request.FINISH:
                self.finish()
            case _:
                pass
        return None
