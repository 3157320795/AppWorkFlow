#!/bin/bash

set -e
# 导出环境变量

WORK_DIR="${COZE_WORKSPACE_PATH:-.}"
PORT=8000
ENABLE_PROXY="${ENABLE_PROXY:-false}"  # 默认禁用代理

usage() {
  echo "用法: $0 -p <端口> [-x <true|false>]"
  echo ""
  echo "参数说明:"
  echo "  -p <端口>        HTTP服务端口（默认: 8000）"
  echo "  -x <true|false>  是否启用代理（默认: false）"
  echo "  -h               显示帮助信息"
  echo ""
  echo "示例:"
  echo "  $0 -p 8080              # 禁用代理启动"
  echo "  $0 -p 8080 -x true      # 启用代理启动"
}

while getopts "p:x:h" opt; do
  case "$opt" in
    p)
      PORT="$OPTARG"
      ;;
    x)
      ENABLE_PROXY="$OPTARG"
      ;;
    h)
      usage
      exit 0
      ;;
    \?)
      echo "无效选项: -$OPTARG"
      usage
      exit 1
      ;;
  esac
done

# 默认禁用代理（国内API不需要）
if [ "$ENABLE_PROXY" != "true" ]; then
  echo "[INFO] 禁用HTTP代理（国内API直连模式）"
  unset HTTP_PROXY
  unset HTTPS_PROXY
  export NO_PROXY="*"
else
  echo "[INFO] 启用HTTP代理"
fi

echo "[INFO] 启动HTTP服务，端口: $PORT"
python ${WORK_DIR}/src/main.py -m http -p $PORT
