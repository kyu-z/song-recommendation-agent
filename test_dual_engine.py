#!/usr/bin/env python3
"""
测试双引擎音乐检索系统
"""
import sys
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

from music_ai_agent import MusicAgent

def test_dual_engine():
    """测试双引擎检索功能"""
    print("🧪 开始测试双引擎音乐检索系统...")
    
    try:
        # 初始化 Agent
        agent = MusicAgent(use_local_model=False)
        print("✅ MusicAgent 初始化成功")
        
        # 测试文本输入
        test_input = "我想听一些安静的夜晚音乐"
        print(f"\n🔍 测试输入: {test_input}")
        
        # 运行推荐
        recommendation = agent.get_recommendation(test_input)
        print(f"\n📝 推荐结果:\n{recommendation}")
        
        print("\n✅ 双引擎测试完成！")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dual_engine()
