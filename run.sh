#!/bin/bash
set -e

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "错误: 未找到虚拟环境，请先运行 python3 -m venv venv"
    exit 1
fi

source venv/bin/activate
echo "开始执行签到..."
python V2free.py
echo "签到完成"
