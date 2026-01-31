"""
Validation prompts for verifying music sources
"""

def get_instrumental_validation_prompt(song_info: dict, search_results: str) -> str:
    """
    Generate validation prompt for instrumental music
    
    Args:
        song_info: Dict containing song and artist information
        search_results: Search results text to validate
    
    Returns:
        Formatted validation prompt
    """
    return f"""检查这些搜索结果，为乐器演奏 "{song_info['song']}" by {song_info['artist']} 找出最高质量的音源：

搜索结果：
{search_results[:1500]}

乐器音乐专用验证标准：
1. **播放量优先**: 高播放量通常代表演奏质量被认可
2. **演奏完整性**: 完整的乐器演奏（避免片段或教学）
3. **音质清晰**: 优先选择音质清晰的录音
4. **不限制官方**: 个人演奏者、音乐学院学生、独立音乐家的优秀演奏都是有效的
5. **平台可靠**: YouTube、SoundCloud等知名平台

优先选择标准：
1. 高播放量的完整演奏版本
2. 标题包含乐器名称和曲目名称
3. 音质清晰的现场或录音室版本
4. 时长合理（通常2-15分钟）

需要避免的内容：
1. 明显的教学视频 ('Tutorial', 'How to play', 'Lesson', 'Learn')
2. 反应视频 ('Reaction', 'Review')
3. 过短的片段（少于1分钟）
4. 明显的翻唱或改编（除非演奏质量很高）

请返回播放量最高且质量最好的一个链接，格式：
{{"link": "URL地址", "platform": "平台名", "title": "视频/音频标题", "match_reason": "选择理由（包含播放量信息）"}}

如果没有找到合适结果，返回null。只返回JSON格式，不要其他文字。"""


def get_popular_music_validation_prompt(song_info: dict, search_results: str) -> str:
    """
    Generate enhanced validation prompt with AI-powered regional and content analysis
    
    Args:
        song_info: Dict containing song and artist information
        search_results: Search results text to validate
    
    Returns:
        Enhanced validation prompt with regional intelligence
    """
    return f"""你是专业的全球音乐验证专家。请为歌曲 "{song_info['song']}" by {song_info['artist']} 找出最可靠的官方音源：

搜索结果：
{search_results[:2000]}

**AI智能验证标准：**

1. **地域与身份智能识别**
   - 利用你的音乐知识库，识别艺人的真实国籍和所属地区
   - 即使标题是全英文，也要基于艺人背景判断地域匹配性
   - 自动识别官方唱片公司：SMTOWN(韩国)、JYPE(韩国)、Avex(日本)、NBCUniversal(日本)等
   - 识别Topic频道（Artist - Topic）作为官方音频频道

2. **视频类型智能分类**
   - Official MV：正式音乐视频（最高优先级）
   - Topic Channel：YouTube自动生成的官方音频频道（高优先级）
   - Lyric Video：歌词视频（中高优先级，支持学习）
   - Audio Only：纯音频版本（中优先级）
   - Live Performance：现场表演（特殊情况高分）
   - Color Coded Lyrics：彩色编码歌词（学习价值，中等优先级）

3. **频道权威性分析**
   - 官方唱片公司频道：如SM Entertainment、JYP Entertainment
   - 艺人官方频道：艺人名 + Official
   - VEVO频道：音乐行业官方分发
   - Topic频道：YouTube官方音频服务
   - 知名音乐平台：大型音乐媒体或平台

4. **智能质量评估**
   - 播放量与时间发布日期的合理性
   - 标题的专业程度和格式规范性
   - 频道订阅数和认证状态
   - 视频描述的完整性和官方感

**过滤排除内容：**
- Cover, Remix (除非用户明确要求变体版本)
- Tutorial, How to play, Lesson, Guide
- Reaction, Review, Analysis (评论类视频)
- Karaoke, Instrumental version (除非用户特别需要)
- Fan made, Amateur, Bootleg (非官方制作)
- 明显的合集：Playlist, Mix, Compilation

**选择优先级排序：**
1. 官方MV > Topic频道 > 官方音频
2. 官方频道 > 认证频道 > 知名平台
3. 高播放量 + 合理发布时间
4. 标题规范 + 描述完整

**地域特殊考虑：**
- K-Pop: 即使全英文标题，优先选择韩国官方来源
- J-Pop: 日本官方频道优先，注意日英混合标题
- C-Pop: 中文/华语音乐，支持简繁体标题

请返回最符合要求的一个链接，必须包含智能分析：
```json
{{
    "link": "URL地址", 
    "platform": "平台名", 
    "title": "视频标题", 
    "content_type": "Official MV/Topic Channel/Lyric Video/Audio Only/Live Performance",
    "channel_authority": "Official Label/Artist Official/VEVO/Topic/Verified/Unknown",
    "region_match": true/false,
    "officialness_score": 0-100,
    "match_reason": "选择理由（包含地域匹配、频道权威性、内容类型分析）"
}}
```

严禁捏造链接。如果没有找到任何符合要求的结果，返回null。只返回JSON格式，不要其他文字。"""
