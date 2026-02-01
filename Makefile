# 変数
COMPOSE = docker-compose

.PHONY: build up5 up13 down logs ps shell

# 1. ビルド（サーバとエージェント両方）
build:
	$(COMPOSE) build

# 2. ゲーム開始準備（一つのプロセスで全員分まわす構成になっている）
up:
	$(COMPOSE) up -d

# # 2. 5人ゲーム開始（エージェントを5体起動）
# up5:
# 	$(COMPOSE) up -d --scale agent=5

# # 3. 13人ゲーム開始（エージェントを13体起動）
# up13:
# 	$(COMPOSE) up -d --scale agent=13

# 4. 全て停止
down:
	$(COMPOSE) down

# 5. エージェント全員のログを追っかける
logs:
	$(COMPOSE) logs -f agent

# 6. 稼働状況の確認（agent.1, agent.2... と並びます）
ps:
	$(COMPOSE) ps

# # 7. 特定のエージェント（1番目）の中で作業する
# # CMDが tail -f /dev/null なので、これを使って中に入ります
# shell:
# 	$(COMPOSE) exec agent-1 /bin/bash

# # 起動中の全エージェントで一斉に Python を実行する
# run-all5:
# 	$(COMPOSE) exec --index=1 agent uv run python src/main.py & \
# 	$(COMPOSE) exec --index=2 agent uv run python src/main.py & \
# 	$(COMPOSE) exec --index=3 agent uv run python src/main.py & \
# 	$(COMPOSE) exec --index=4 agent uv run python src/main.py & \
# 	$(COMPOSE) exec --index=5 agent uv run python src/main.py
