import os

# Coze API 配置
COZE_API_BASE_URL = "https://api.coze.com/open_api/v2/chat"
COZE_API_KEY = os.getenv("COZE_API_KEY", "your-coze-api-key-here")

# Stitch MCP 配置
MCP_URL = "https://stitch.googleapis.com/mcp"
MCP_HEADERS = {
    "X-Goog-Api-Key": "AQ.Ab8RN6J3ydkw2EWwp-XtY9TPwwt8KooPdw2_Z0G0DL94tymgZA",
    "Content-Type": "application/json"
}
