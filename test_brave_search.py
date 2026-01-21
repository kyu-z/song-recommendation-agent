#!/usr/bin/env python3
"""
测试Brave Search集成
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

# Load environment variables
load_dotenv(".env.local")

# Import the updated MusicAgent
from music_ai_agent import MusicAgent, BraveSearchTool

def test_brave_search_tool():
    """测试Brave Search工具"""
    print("=== 测试Brave Search工具 ===")
    
    api_key = os.getenv('Brave_Search_API_KEY')
    if not api_key:
        print("❌ Brave_Search_API_KEY not found in environment")
        return False
    
    try:
        brave_tool = BraveSearchTool(api_key)
        
        # 测试简单搜索
        test_query = "best jazz songs for rainy night reddit -site:youtube.com"
        print(f"🔍 测试搜索: {test_query}")
        
        results = brave_tool.run(test_query, count=5)
        print(f"✅ 搜索成功，结果长度: {len(results)} 字符")
        print(f"前200字符: {results[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Brave Search工具测试失败: {e}")
        return False

def test_music_agent_initialization():
    """测试MusicAgent初始化"""
    print("\n=== 测试MusicAgent初始化 ===")
    
    try:
        agent = MusicAgent(use_local_model=False)
        
        if agent.brave_search:
            print("✅ Brave Search成功集成到MusicAgent")
        else:
            print("⚠️  Brave Search未能初始化")
        
        # 测试基本功能
        agent_info = agent.get_agent_info()
        print(f"📊 Agent信息: {agent_info}")
        
        return True
        
    except Exception as e:
        print(f"❌ MusicAgent初始化失败: {e}")
        return False

def test_simple_recommendation():
    """测试简单推荐功能"""
    print("\n=== 测试简单推荐 ===")
    
    try:
        agent = MusicAgent(use_local_model=False)
        
        # 使用简单的文本输入测试
        test_input = "我想听一些放松的爵士乐"
        print(f"🎵 用户输入: {test_input}")
        
        recommendation = agent.get_recommendation(test_input)
        print(f"📝 推荐结果:\n{recommendation}")
        
        return True
        
    except Exception as e:
        print(f"❌ 推荐测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试Brave Search集成")
    
    # 测试1: Brave Search工具
    search_ok = test_brave_search_tool()
    
    # 测试2: MusicAgent初始化
    init_ok = test_music_agent_initialization()
    
    # 测试3: 简单推荐（如果前面都成功的话）
    if search_ok and init_ok:
        test_simple_recommendation()
    
    print("\n🏁 测试完成")
