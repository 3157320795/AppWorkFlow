import os

# Coze API 配置
COZE_API_BASE_URL = "https://api.coze.com/open_api/v2/chat"
COZE_API_KEY = os.getenv("COZE_API_KEY", "your-coze-api-key-here")

# Stitch MCP（实际请求与 Header 封装见 graphs.stitch_mcp）
MCP_URL = "https://stitch.googleapis.com/mcp"


def stitch_mcp_headers() -> dict:
    from graphs.stitch_mcp import stitch_headers

    try:
        return stitch_headers()
    except ValueError:
        return {}
