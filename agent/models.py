"""
Model Manager for Music AI Agent
Supports switching between GPT-4o-mini and local Ollama models
"""
import base64
import os
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv(".env.local")

class ModelManager:
    """
    Unified model interface supporting both OpenAI and Ollama models
    """
    
    def __init__(self, use_local_model: bool = False):
        """
        Initialize model manager
        
        Args:
            use_local_model: If True, use local Ollama models; otherwise use OpenAI
        """
        self.use_local = use_local_model
        self._setup_models()
    
    def _setup_models(self):
        """Setup models based on configuration"""
        if self.use_local:
            try:
                from langchain_community.llms import Ollama
                self.vision_model = Ollama(model="qwen2.5:1.5b")
                self.text_model = Ollama(model="qwen2.5:1.5b")
                print("🤖 Using local Ollama models (Qwen2.5:1.5b)")
            except ImportError:
                print("⚠️  Ollama not available, falling back to OpenAI")
                self.use_local = False
                self._setup_openai_models()
        else:
            self._setup_openai_models()
    
    def _setup_openai_models(self):
        """Setup OpenAI models"""
        self.vision_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.8)
        self.text_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.8)
        print("🌐 Using OpenAI models (GPT-4o-mini)")
    
    def _encode_image_for_openai(self, image_path: str) -> str:
        """Encode image for OpenAI format"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def _encode_image_for_ollama(self, image_path: str) -> str:
        """Encode image for Ollama format (may differ from OpenAI)"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def invoke_vision(self, image_path: str, prompt: str) -> str:
        """
        Unified vision model invocation
        
        Args:
            image_path: Path to the image file
            prompt: Text prompt for analysis
            
        Returns:
            Model response as string
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        if self.use_local:
            # Ollama vision handling
            try:
                base64_image = self._encode_image_for_ollama(image_path)
                # Note: Ollama vision interface might need adjustment based on actual API
                response = self.vision_model.invoke(f"{prompt}\n[Image: {image_path}]")
                return response
            except Exception as e:
                print(f"⚠️  Ollama vision failed, falling back to text-only: {e}")
                return self.text_model.invoke(prompt)
        else:
            # OpenAI vision handling
            base64_image = self._encode_image_for_openai(image_path)
            
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            )
            
            response = self.vision_model.invoke([message])
            return response.content.strip()
    
    def invoke_text(self, prompt: str) -> str:
        """
        Unified text model invocation
        
        Args:
            prompt: Text prompt
            
        Returns:
            Model response as string
        """
        if self.use_local:
            response = self.text_model.invoke(prompt)
            return response if isinstance(response, str) else str(response)
        else:
            response = self.text_model.invoke(prompt)
            return response.content.strip()
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about current models"""
        return {
            "use_local": self.use_local,
            "vision_model": "qwen2.5:1.5b" if self.use_local else "gpt-4o-mini",
            "text_model": "qwen2.5:1.5b" if self.use_local else "gpt-4o-mini",
            "provider": "Ollama" if self.use_local else "OpenAI"
        }


# Test script
if __name__ == "__main__":
    # Test with OpenAI
    print("Testing OpenAI models...")
    openai_manager = ModelManager(use_local=False)
    print(openai_manager.get_model_info())
    
    # Test text invocation
    response = openai_manager.invoke_text("Hello, how are you?")
    print(f"Text response: {response}")
    
    # Test with local models (if available)
    print("\nTesting local models...")
    local_manager = ModelManager(use_local=True)
    print(local_manager.get_model_info())
    
    if local_manager.use_local:
        response = local_manager.invoke_text("Hello, how are you?")
        print(f"Local text response: {response}")
