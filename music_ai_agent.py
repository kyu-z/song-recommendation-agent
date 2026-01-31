import os
import sys
from pathlib import Path
from typing import Dict, Any
from langchain_core.runnables import RunnableLambda
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from database.vector_store import MusicVectorStore
from agent.models import ModelManager
from agent.tools import MusicSearchTool
from external.brave_search import BraveSearchTool
from agent.chains.perception import PerceptionChain
from agent.chains.discovery import DiscoveryChain
from agent.chains.decision import DecisionChain
from agent.chains.generation import GenerationChain

load_dotenv(".env.local")


class MusicAgent:
    """
    Music AI Agent with modular chain architecture
    
    Refactored to use separate chain components for better maintainability:
    - PerceptionChain: Understanding user intent
    - DiscoveryChain: Music discovery through web search
    - DecisionChain: Source finding and selection
    - GenerationChain: Final response generation
    """
    
    def __init__(self, use_local_model: bool = False):
        """
        Initialize Music Agent with chain components
        
        Args:
            use_local_model: Whether to use local models (currently disabled)
        """
        # Initialize core components
        self.model_manager = ModelManager(use_local_model)
        self.vector_store = MusicVectorStore()
        self.music_search = MusicSearchTool(self.vector_store)
        
        # Initialize external services
        brave_api_key = os.getenv("BRAVE_API_KEY")
        self.brave_search = BraveSearchTool(brave_api_key) if brave_api_key else None
        
        # Initialize processing chains
        self.perception_chain = PerceptionChain(self.model_manager)
        self.discovery_chain = DiscoveryChain(self.brave_search, self.model_manager)
        self.decision_chain = DecisionChain(self.brave_search, self.model_manager)
        self.generation_chain = GenerationChain(self.model_manager)
        
        # Build main processing chain
        self._build_main_chain()
        
        print(f"🤖 Music Agent initialized")
        print(f"   - Model: {self.model_manager.get_model_info()}")
        print(f"   - Vector DB: {self.vector_store.collection.count()} songs")
        print(f"   - Brave Search: {'✅' if self.brave_search else '❌'}")
    
    def _build_main_chain(self):
        """Build the main processing chain using LCEL"""
        # Define processing stages as RunnableLambda functions
        self.perception_stage = RunnableLambda(self._perception_stage)
        self.retrieval_stage = RunnableLambda(self._retrieval_stage)
        self.decision_stage = RunnableLambda(self._decision_stage)
        self.generation_stage = RunnableLambda(self._generation_stage_with_context_save)
        
        # Compose main chain
        self.main_chain = (
            self.perception_stage |
            self.retrieval_stage |
            self.decision_stage |
            self.generation_stage
        )
    
    async def recommend(self, user_input: str) -> Dict[str, Any]:
        """
        Main recommendation interface
        
        Args:
            user_input: User input (text or image path)
            
        Returns:
            Complete recommendation result
        """
        try:
            # Execute stages sequentially with async support
            context = self._perception_stage(user_input)
            context = await self._retrieval_stage(context)
            context = self._decision_stage(context)
            result = self._generation_stage_with_context_save(context)
            return result
        except Exception as e:
            print(f"❌ Recommendation failed: {e}")
            return {
                'raw_input': user_input,
                'search_goal': '',
                'found_songs': [],
                'final_report': f'推荐失败: {str(e)}'
            }
    
    def _perception_stage(self, user_input: str) -> Dict[str, Any]:
        """Stage 1: Delegate to PerceptionChain"""
        return self.perception_chain.process(user_input)
    
    async def _retrieval_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 2: Delegate to DiscoveryChain"""
        print("🎵 [检索阶段] 开始全网音乐搜索...")
        return await self.discovery_chain.search(context)
    
    def _decision_stage(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 3: Delegate to DecisionChain"""
        return self.decision_chain.select(context)
    
    def _generation_stage_with_context_save(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 4: Delegate to GenerationChain and save context"""
        result = self.generation_chain.generate(context)
        
        # Save context for debugging/analysis
        self.last_context = result
        
        return result


# Backward compatibility - alias for the old class name
MusicAIExplorer = MusicAgent


if __name__ == "__main__":
    # Test the refactored agent
    print("\n--- 🎵 重构后的音乐推荐系统测试 ---")
    
    # Test with OpenAI models
    print("\n=== 使用 OpenAI 模型测试 ===")
    agent = MusicAgent(use_local_model=False)
    
    # Test text input
    print("\n📝 测试文字输入:")
    result = agent.recommend("rock music")
    print(f"推荐结果: {len(result.get('found_songs', []))} 首歌曲")
    
    print("\n✅ 重构完成！新的模块化架构已就绪。")
