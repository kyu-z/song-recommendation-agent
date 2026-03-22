"""
Perception Chain - Stage 1: Understanding user intent
"""
import os
import re
import json
from typing import Dict, Any
from ..prompts.perception import get_vision_prompt, get_text_processing_prompt


class PerceptionChain:
    """Handles user input perception and intent understanding"""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
    
    def process(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input and extract search intent with standardized context
        
        Args:
            user_input: Raw user input (text or image path)
            
        Returns:
            Standardized context dict with comprehensive metadata
        """
        # Initialize standardized context schema
        context = {
            'raw_input': user_input,
            'search_goal': '',           # 展示用的搜索目标
            'refined_query': '',         # 纯净的搜索词
            'native_name': None,         # 艺人母语原名
            'origin_region': 'unknown',  # 地域标签
            'search_strategy': 'international',  # 搜索策略
            'is_specific': False,        # 是否为特定作品搜索
            'vocal_type': 'unknown',     # 'vocal', 'instrumental', 'unknown'
            'music_type': 'unknown',     # 'pop', 'classical', 'ost', 'ambient', 'unknown'
            'found_songs': [],
            'final_report': '',
            'cultural_tags': [],
        }
        
        # Check if input is an image
        if os.path.isfile(user_input) and user_input.lower().endswith(('.png', '.jpg', '.jpeg')):
            context['is_image'] = True
            context = self._process_image(user_input, context)
        else:
            context['is_image'] = False
            context = self._process_text(user_input, context)
        
        print(f"🎯 [感知完成] 标准化Context: {context}")
        return context
    
    def _process_image(self, image_path: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process image input using vision model"""
        vision_prompt = get_vision_prompt()
        
        try:
            analysis_result = self.model_manager.invoke_vision(image_path, vision_prompt)
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', analysis_result, re.DOTALL)
            if json_match:
                print(f"🖼️  [调试] 找到JSON: {json_match.group()}")
                parsed = json.loads(json_match.group())
                raw_search_goal = parsed.get('search_goal', '').strip()
                tags = parsed.get('cultural_tags')
                context['cultural_tags'] = tags if isinstance(tags, list) else []
                
                # Clean search terms: take the main part before comma, remove redundant descriptions
                if ',' in raw_search_goal:
                    context['search_goal'] = raw_search_goal.split(',')[0].strip()
                    context['refined_query'] = context['search_goal']
                else:
                    context['search_goal'] = raw_search_goal
                    context['refined_query'] = raw_search_goal
                
                # Set defaults for image processing
                context['is_specific'] = False
                context['vocal_type'] = 'unknown'
                context['music_type'] = 'ambient'  # Images often suggest atmospheric music
                    
                print(f"🖼️  [视觉感知] 原始: {raw_search_goal}")
                print(f"🖼️  [视觉感知] 清理后: {context['search_goal']}")
            else:
                print(f"🖼️  [调试] 未找到JSON，使用备用词汇")
                context['search_goal'] = 'atmospheric music'
                context['refined_query'] = 'atmospheric music'
                context['is_specific'] = False
                context['vocal_type'] = 'instrumental'
                context['music_type'] = 'ambient'
                
        except Exception as e:
            print(f"🖼️  视觉分析失败: {e}")
            context['search_goal'] = 'background music'
            context['refined_query'] = 'background music'
            context['is_specific'] = False
            context['vocal_type'] = 'instrumental'
            context['music_type'] = 'ambient'
        
        return context
    
    def _process_text(self, text_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process text input using LLM for intelligent parsing"""
        print(f"📝 [文字感知] 原始输入: {text_input}")
        
        # Get text processing prompt
        processing_prompt = get_text_processing_prompt(text_input)
        
        try:
            # Use LLM to parse and refine the text input
            processing_result = self.model_manager.invoke_text(processing_prompt)
            
            print(f"📝 [LLM处理] 响应: {processing_result}")
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', processing_result, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                
                context['search_goal'] = parsed.get('search_goal', text_input).strip()
                context['refined_query'] = parsed.get('refined_query', text_input).strip()
                context['native_name'] = parsed.get('native_name')
                context['origin_region'] = parsed.get('origin_region', 'unknown')
                context['search_strategy'] = parsed.get('search_strategy', 'international')
                context['is_specific'] = parsed.get('is_specific', False)
                context['vocal_type'] = parsed.get('vocal_type', 'unknown')
                context['music_type'] = parsed.get('music_type', 'unknown')
                
                print(f"📝 [解析成功]:")
                print(f"   - 搜索目标: {context['search_goal']}")
                print(f"   - 精炼查询: {context['refined_query']}")
                print(f"   - 母语原名: {context['native_name']}")
                print(f"   - 地域标签: {context['origin_region']}")
                print(f"   - 搜索策略: {context['search_strategy']}")
                print(f"   - 特定作品: {context['is_specific']}")
                print(f"   - 人声类型: {context['vocal_type']}")
                print(f"   - 音乐类型: {context['music_type']}")
                
            else:
                print("📝 [解析失败] 使用简单回退逻辑")
                context = self._simple_text_fallback(text_input, context)
                
        except Exception as e:
            print(f"📝 [LLM处理失败] {e}")
            context = self._simple_text_fallback(text_input, context)
        
        return context
    
    def _simple_text_fallback(self, text_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Simple fallback logic when LLM processing fails"""
        cleaned = text_input.strip().lower()
        
        # Set basic values
        context['search_goal'] = text_input.strip()
        
        # Enhanced refined_query with year detection
        context['refined_query'] = self._enhance_query_with_year_detection(cleaned)
        
        # Simple heuristics for classification
        specific_indicators = ['anime', 'pokemon', 'zelda', 'ghibli', 'ost', 'soundtrack', 'theme']
        context['is_specific'] = any(indicator in cleaned for indicator in specific_indicators)
        
        instrumental_indicators = ['instrumental', '纯音乐', 'piano', 'classical', 'ambient']
        if any(indicator in cleaned for indicator in instrumental_indicators):
            context['vocal_type'] = 'instrumental'
        elif 'vocal' in cleaned or 'song' in cleaned:
            context['vocal_type'] = 'vocal'
        else:
            context['vocal_type'] = 'unknown'
        
        # Basic music type detection
        if any(word in cleaned for word in ['ost', 'soundtrack', 'theme', 'anime']):
            context['music_type'] = 'ost'
        elif any(word in cleaned for word in ['classical', 'piano', 'orchestra']):
            context['music_type'] = 'classical'
        elif any(word in cleaned for word in ['pop', 'rock', 'jazz', 'hip hop']):
            context['music_type'] = 'pop'
        elif any(word in cleaned for word in ['ambient', 'atmospheric', 'chill']):
            context['music_type'] = 'ambient'
        else:
            context['music_type'] = 'pop'  # Default to pop
        
        # Basic region detection for search strategy
        if any(word in cleaned for word in ['kpop', 'k-pop', 'korean', '韩国']):
            context['origin_region'] = 'Korea'
        elif any(word in cleaned for word in ['jpop', 'j-pop', 'japanese', '日本']):
            context['origin_region'] = 'Japan'
        elif any(word in cleaned for word in ['cpop', 'c-pop', 'chinese', '中文', '华语']):
            context['origin_region'] = 'Greater China'
        else:
            context['origin_region'] = 'Western'
            
        context['search_strategy'] = 'international'
        context['native_name'] = None
        
        print(f"📝 [简单回退] 分类结果: specific={context['is_specific']}, vocal={context['vocal_type']}, type={context['music_type']}")
        
        return context
    
    def _enhance_query_with_year_detection(self, cleaned_input: str) -> str:
        """Enhanced query generation with year-specific optimization"""
        # Detect year patterns
        year_pattern = r'\b(19\d{2}|20\d{2})\b'
        year_matches = re.findall(year_pattern, cleaned_input)
        
        if year_matches:
            year = year_matches[0]
            print(f"📝 [年份检测] 发现年份: {year}")
            
            # Genre-specific year query enhancement
            if any(word in cleaned_input for word in ['kpop', 'k-pop', 'korean']):
                return f"K-Pop hits {year} chart best songs released Korean music"
            elif any(word in cleaned_input for word in ['jpop', 'j-pop', 'japanese']):
                return f"J-Pop chart {year} Oricon annual ranking Japanese hits"
            elif any(word in cleaned_input for word in ['cpop', 'c-pop', 'chinese', 'mandarin']):
                return f"C-Pop {year} Chinese music chart hits Mandarin songs"
            elif any(word in cleaned_input for word in ['pop', 'music', 'hits']):
                return f"Billboard Hot 100 {year} chart top songs year-end"
            else:
                return f"music hits {year} chart annual best songs"
        
        # No year detected, return cleaned input
        return cleaned_input
