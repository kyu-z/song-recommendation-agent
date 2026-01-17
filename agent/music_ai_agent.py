import os
import base64
import re
import random
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from database.vector_store import MusicVectorStore
from dotenv import load_dotenv

load_dotenv(".env.local")

class MusicAIExplorer:
    def __init__(self):
        # gpt-4o-mini 支持多模态识图
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.8)
        self.vs = MusicVectorStore()

    def _encode_image(self, image_path):
        """将图片转换为 Base64 编码"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def get_recommendation(self, user_input):
        # 0. 获取流派池
        existing_genres = self.vs.collection.get(include=['metadatas'])['metadatas']
        unique_genres = list(set([m.get('genre') for m in existing_genres if m.get('genre')]))
        genres_pool = ", ".join(unique_genres)

        is_image = False
        image_analysis = ""
        
        if os.path.isfile(user_input) and user_input.lower().endswith(('.png', '.jpg', '.jpeg')):
            is_image = True
            base64_image = self._encode_image(user_input)
            
            # 使用 f-string 确保 genres_pool 被正确注入
            image_message = HumanMessage(
                content=[
                    {"type": "text", 
                     "text": f"分析这张图片的意境。然后从以下流派中选出1个最匹配的单词：[{genres_pool}]。注意：直接输出单词本身，不要带标点符号，不要解释。"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            )
            # 因为 Prompt 要求只输出单词，所以直接 strip 即可
            suggested_genre = self.llm.invoke([image_message]).content.strip().lower()
            image_analysis = f"这张图散发着一种 {suggested_genre} 的氛围。"
            query_text = f"这张图片的视觉意境"
        else:
            # 文字模式
            keyword_prompt = f"根据描述 '{user_input}'，从以下流派中选出一个最匹配的：[{genres_pool}]。仅输出单词，不要标点。"
            suggested_genre = self.llm.invoke(keyword_prompt).content.strip().lower()
            image_analysis = f"听众想要这种感觉: {user_input}"
            query_text = user_input

        # 清洗一下 suggested_genre，防止 AI 顺手加了句号
        suggested_genre = re.sub(r'[^\w\s]', '', suggested_genre)
        print(f"🔍 [感知系统] 确定的流派: {suggested_genre}")

        # 2. 第二阶段：检索
        results = self.vs.collection.get(
            where={"genre": suggested_genre},
            include=['metadatas'],
            limit=15
        )

        music_list = results.get('metadatas', [])

        if not music_list:
            return f"抱歉，关于 '{suggested_genre}' 的音乐，我的收藏夹暂时还是空白。"

        random.shuffle(music_list)
        
        candidates = ""
        for i, m in enumerate(music_list):
            candidates += f"候选{i+1}: 标题: {m.get('title')}, 描述: {m.get('model_tag')}\n"

        selection_prompt = f"""
        你是一位感性的音乐主理人。
        图片/环境意境描述: {image_analysis}
        
        曲库候选名单：
        {candidates}
        
        请从中选出 1 首意境最贴合的歌。只需回复数字索引（如: 1）。
        """
        
        selected_res = self.llm.invoke(selection_prompt).content.strip()
        
        try:
            # 更加稳健的数字提取
            match = re.search(r'\d+', selected_res)
            idx = int(match.group()) - 1
            # 确保索引不越界
            idx = max(0, min(idx, len(results['metadatas']) - 1))
            music_data = results['metadatas'][idx]
            print(f"🎯 [智能决策] AI 选中了: {music_data.get('title')}")
        except:
            music_data = random.choice(results['metadatas'])

        # 4. 第四阶段：感性推荐语生成
        prompt = ChatPromptTemplate.from_template("""
        你是一位感性、温柔的深夜电台音乐主理人。
        
        听众的需求/图片意境是: "{query}"
        
        你决定推荐这首歌:
        - 标题: {title}
        - 风格: {genre}
        - AI 捕捉到的隐藏韵律: {model_tag}
        
        请用自然、动人的语言告诉听众，为什么你觉得这首歌和此时此刻的氛围是最完美的搭配。
        """)

        chain = prompt | self.llm
        response = chain.invoke({
            "query": query_text,
            "title": music_data.get('title'),
            "genre": music_data.get('genre'),
            "model_tag": music_data.get('model_tag')
        })

        return response.content
if __name__ == "__main__":
    explorer = MusicAIExplorer()
    print("\n--- 🌙 深夜音乐馆：视觉与听觉联觉模式已开启 ---")
    
    # 测试方式 1：纯文字
    # test_input = "我想要一点迷幻且复古的音乐"
    
    # 测试方式 2：图片路径（请确保你本地有这张图）
    test_input = "img/music_img.jpg" 
    
    if os.path.exists(test_input) or not test_input.endswith(('.jpg', '.png')):
        print(f"\n你的输入: {test_input}")
        print(f"\n主理人给你的回信: \n\n{explorer.get_recommendation(test_input)}")
    else:
        print(f"⚠️ 未找到图片文件: {test_input}，请检查路径。")