#!/bin/bash
set -e

echo -e "\e[36mStopping Letta containers...\e[0m"
docker compose --env-file .env2 down

echo -e "\e[33mWiping old PostgreSQL data in ./data/pgdata/...\e[0m"
if [ -d "./data/pgdata" ]; then
    # Wipe all contents within the directory (including hidden files) but keep the directory itself
    sudo rm -rf ./data/pgdata/* ./data/pgdata/.* 2>/dev/null || true
    # Re-ensure the directory exists if rm overreached
    mkdir -p ./data/pgdata
    echo -e "\e[32mData wiped successfully.\e[0m"
else
    echo -e "\e[32mNo data found or folder is already empty.\e[0m"
fi

echo -e "\e[36mStarting Letta containers with new environment...\e[0m"
docker compose --env-file .env2 up -d

echo -e "\e[32mDone! New fresh database is initializing.\e[0m"
