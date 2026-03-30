#!/usr/bin/env python3
"""
查询 Stitch 项目信息的简单脚本
"""
import os
import json
import sys

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

# 添加 src 到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
from src.graphs.stitch_mcp import (
    TOOL_GET_PROJECT,
    TOOL_LIST_SCREENS,
    call_stitch_tool,
    stitch_headers,
    _get_stitch_api_key,
    SHORT_TIMEOUT,
)


def parse_stitch_response(result: dict) -> dict:
    """解析 Stitch MCP 响应，处理嵌套 JSON 字符串"""
    if not isinstance(result, dict):
        return {}
    
    # 获取 result 字段
    res = result.get("result", {})
    
    # 处理 content 数组
    if isinstance(res, dict) and "content" in res:
        content = res.get("content", [])
        if content and isinstance(content[0], dict):
            text = content[0].get("text", "")
            if text:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass
    
    return res


def query_project(project_id: str):
    """查询 Stitch 项目信息"""
    
    # 获取 API Key
    api_key = _get_stitch_api_key()
    if not api_key:
        print("❌ 错误: 未找到 GOOGLE_STITCH_API_KEY 环境变量")
        print("请在 .env 文件中设置 GOOGLE_STITCH_API_KEY")
        return
    
    print(f"🔍 正在查询项目: {project_id}")
    print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")
    print("-" * 60)
    
    headers = stitch_headers(api_key)
    
    with httpx.Client(timeout=SHORT_TIMEOUT) as client:
        # 1. 查询项目基本信息
        print("\n📋 1. 项目基本信息 (get_project)")
        status, result = call_stitch_tool(
            client,
            headers=headers,
            tool_name=TOOL_GET_PROJECT,
            arguments={"name": f"projects/{project_id}"},
            rpc_id=f"query:{project_id}",
        )
        
        print(f"   HTTP 状态: {status}")
        
        if status != 200:
            print(f"   ❌ 查询失败: {result}")
            return
        
        if isinstance(result, dict) and result.get("error"):
            print(f"   ❌ 错误: {result.get('error')}")
            return
        
        # 解析项目数据
        project_data = parse_stitch_response(result)
        
        if not project_data:
            print(f"   ⚠️ 未找到项目数据")
            print(f"   原始响应: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}")
            return
        
        print(f"   ✅ 项目ID: {project_data.get('name', 'N/A').split('/')[-1]}")
        print(f"   📛 项目名称: {project_data.get('title', project_data.get('displayName', 'N/A'))}")
        print(f"   📝 描述: {project_data.get('description', 'N/A')[:50]}...")
        print(f"   🔒 可见性: {project_data.get('visibility', 'N/A')}")
        
        create_time = project_data.get('createTime', 'N/A')
        update_time = project_data.get('updateTime', 'N/A')
        print(f"   📅 创建时间: {create_time}")
        print(f"   🔄 更新时间: {update_time}")
        
        # 缩略图
        thumbnail = project_data.get('thumbnailScreenshot', {})
        if thumbnail:
            print(f"   🖼️ 缩略图: {thumbnail.get('downloadUrl', 'N/A')[:60]}...")
        
        # 设计主题
        design_theme = project_data.get('designTheme', {})
        if design_theme:
            print(f"\n   🎨 设计主题:")
            print(f"      - 字体: {design_theme.get('font', 'N/A')}")
            print(f"      - 主色: {design_theme.get('overridePrimaryColor', design_theme.get('customColor', 'N/A'))}")
            print(f"      - 圆角: {design_theme.get('roundness', 'N/A')}")
            print(f"      - 模式: {design_theme.get('colorMode', design_theme.get('colorVariant', 'N/A'))}")
        
        # 2. 查询 Screens 列表
        print("\n\n🖼️ 2. Screens 列表 (list_screens)")
        status2, result2 = call_stitch_tool(
            client,
            headers=headers,
            tool_name=TOOL_LIST_SCREENS,
            arguments={"projectId": project_id},
            rpc_id=f"query:list:{project_id}",
        )
        
        print(f"   HTTP 状态: {status2}")
        
        if status2 != 200:
            print(f"   ❌ 查询失败: {result2}")
            return
        
        screens_data = parse_stitch_response(result2)
        screens = screens_data.get("screens", [])
        
        print(f"   📊 Screens 数量: {len(screens)}")
        
        if screens:
            for i, screen in enumerate(screens, 1):
                screen_id = screen.get('id', 'N/A')
                name = screen.get('name', 'N/A')
                prompt = screen.get('prompt', '')[:40]
                
                # 检查是否有资源
                screenshot = screen.get('screenshot', {})
                html_code = screen.get('htmlCode', {})
                has_screenshot = bool(screenshot.get('downloadUrl'))
                has_html = bool(html_code.get('downloadUrl'))
                
                status_icon = "✅" if (has_screenshot and has_html) else "⏳"
                
                print(f"\n   {status_icon} Screen #{i}: {name}")
                print(f"      ID: {screen_id}")
                if prompt:
                    print(f"      提示词: {prompt}...")
                print(f"      截图: {'✅ 有' if has_screenshot else '❌ 无'}")
                print(f"      HTML: {'✅ 有' if has_html else '❌ 无'}")
                
                if has_screenshot:
                    print(f"      📷 截图URL: {screenshot.get('downloadUrl', 'N/A')[:60]}...")
                if has_html:
                    print(f"      📄 HTML URL: {html_code.get('downloadUrl', 'N/A')[:60]}...")
        else:
            print("   ⚠️ 该项目暂无 Screens")
        
        # Screen 实例（画布上的位置）
        screen_instances = project_data.get('screenInstances', [])
        if screen_instances:
            print(f"\n   📐 画布布局: {len(screen_instances)} 个实例")
            for si in screen_instances:
                if si.get('type') == 'DESIGN_SYSTEM_INSTANCE':
                    continue
                print(f"      - Screen {si.get('sourceScreen', '').split('/')[-1][:8]}... @ ({si.get('x', 0)}, {si.get('y', 0)}) {si.get('width')}x{si.get('height')}")
    
    print("\n" + "=" * 60)
    print("✅ 查询完成")


if __name__ == "__main__":
    # 默认查询用户提供的项目ID
    DEFAULT_PROJECT_ID = "16162892868949884574"
    
    # 支持命令行参数
    project_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROJECT_ID
    
    query_project(project_id)
