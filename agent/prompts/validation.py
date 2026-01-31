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
    Generate validation prompt for popular music
    
    Args:
        song_info: Dict containing song and artist information
        search_results: Search results text to validate
    
    Returns:
        Formatted validation prompt
    """
    return f"""检查这些搜索结果，为歌曲 "{song_info['song']}" by {song_info['artist']} 找出最可靠的官方音源：

搜索结果：
{search_results[:1500]}

流行音乐验证标准：
1. 优先YouTube、Spotify、Apple Music等知名平台
2. 标题包含歌曲名或艺人名的核心关键词即可（不需要完全匹配）
3. 来自YouTube且标题相关的视频都视为有效
4. 不是明显的合集、播放列表标题（避免"playlist"、"mix"、"compilation"等词）
5. 优先官方版本，但不过度严格要求

注意过滤以下内容：
1. 标题包含 'Cover', 'Remix' (除非用户要求), 'Tutorial', 'How to play', 'Lesson'
2. 时长过短（少于2分钟）的片段或预览
3. 包含 'reaction', 'review', 'analysis' 的评论视频
4. 'karaoke', 'instrumental version' (除非用户明确要求)

优先选择：
1. 官方频道或知名音乐平台上传的内容
2. 完整版歌曲（通常3-6分钟正常时长）
3. 标题简洁直接，包含歌曲名和艺人名
4. 高播放量或来源可靠的版本

请返回最符合要求的一个链接，格式：
{{"link": "URL地址", "platform": "平台名", "title": "视频/音频标题", "match_reason": "匹配理由"}}

如果没有找到任何相关结果，返回null。只返回JSON格式，不要其他文字。"""
