#!/usr/bin/env python3
"""
数字分身功能的独立测试（不依赖fastmcp）
"""

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

# 数据库初始化
DB_PATH = "digital_twin_test.db"

@dataclass
class ChatMessage:
    """聊天消息数据结构"""
    message_type: str  # 'sent' or 'received'
    content: str
    timestamp: str
    contact_name: str = ""

@dataclass
class UserProfile:
    """用户画像数据结构"""
    interests: List[str]
    personality: Dict[str, Any]
    communication_style: Dict[str, Any]
    frequent_topics: List[str]

def init_database():
    """初始化数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建聊天记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message_type TEXT NOT NULL,  -- 'sent' or 'received'
            content TEXT NOT NULL,
            timestamp TIMESTAMP,
            contact_name TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # 创建用户画像表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            interests TEXT,  -- JSON格式存储兴趣爱好
            personality TEXT,  -- JSON格式存储性格特征
            communication_style TEXT,  -- JSON格式存储沟通风格
            frequent_topics TEXT,  -- JSON格式存储常聊话题
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()

class DigitalTwin:
    """数字分身核心类"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.conn = sqlite3.connect(DB_PATH)
        
    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()
    
    def import_wechat_data(self, messages: List[ChatMessage]) -> Dict[str, Any]:
        """导入微信聊天记录"""
        cursor = self.conn.cursor()
        imported_count = 0
        
        for msg in messages:
            try:
                cursor.execute("""
                    INSERT INTO chat_records (user_id, message_type, content, timestamp, contact_name)
                    VALUES (?, ?, ?, ?, ?)
                """, (self.user_id, msg.message_type, msg.content, msg.timestamp, msg.contact_name))
                imported_count += 1
            except sqlite3.Error as e:
                print(f"导入消息失败: {e}")
                
        self.conn.commit()
        return {
            "imported_count": imported_count,
            "total_messages": len(messages),
            "success": True
        }
    
    def analyze_user_profile(self) -> UserProfile:
        """分析用户画像"""
        cursor = self.conn.cursor()
        
        # 获取所有聊天记录
        cursor.execute("""
            SELECT message_type, content, contact_name 
            FROM chat_records 
            WHERE user_id = ?
        """, (self.user_id,))
        
        records = cursor.fetchall()
        
        # 简单的文本分析来构建用户画像
        sent_messages = [r[1] for r in records if r[0] == 'sent']
        received_messages = [r[1] for r in records if r[0] == 'received']
        
        # 分析兴趣爱好（基于关键词）
        interests = self._extract_interests(sent_messages)
        
        # 分析性格特征
        personality = self._analyze_personality(sent_messages)
        
        # 分析沟通风格
        communication_style = self._analyze_communication_style(sent_messages)
        
        # 分析常聊话题
        frequent_topics = self._extract_topics(sent_messages + received_messages)
        
        profile = UserProfile(
            interests=interests,
            personality=personality,
            communication_style=communication_style,
            frequent_topics=frequent_topics
        )
        
        # 保存到数据库
        self._save_user_profile(profile)
        
        return profile
    
    def _extract_interests(self, messages: List[str]) -> List[str]:
        """提取兴趣爱好"""
        interest_keywords = {
            "运动": ["跑步", "健身", "篮球", "足球", "游泳", "瑜伽", "爬山"],
            "音乐": ["音乐", "歌曲", "演唱会", "乐器", "唱歌"],
            "电影": ["电影", "影院", "导演", "演员", "剧情"],
            "美食": ["美食", "餐厅", "做饭", "菜谱", "好吃"],
            "旅游": ["旅游", "旅行", "景点", "酒店", "机票"],
            "读书": ["读书", "书籍", "小说", "作者", "阅读"],
            "游戏": ["游戏", "手游", "电竞", "主机"],
            "科技": ["科技", "手机", "电脑", "AI", "编程"]
        }
        
        interests = []
        text = " ".join(messages)
        
        for interest, keywords in interest_keywords.items():
            if any(keyword in text for keyword in keywords):
                interests.append(interest)
                
        return interests
    
    def _analyze_personality(self, messages: List[str]) -> Dict[str, Any]:
        """分析性格特征"""
        text = " ".join(messages)
        
        personality = {
            "活跃度": "中等",
            "幽默感": "一般",
            "表达方式": "直接"
        }
        
        # 简单的情感分析
        positive_words = ["哈哈", "😄", "开心", "棒", "好的", "谢谢", "不错"]
        negative_words = ["郁闷", "烦", "累", "难受", "😢"]
        
        positive_count = sum(text.count(word) for word in positive_words)
        negative_count = sum(text.count(word) for word in negative_words)
        
        if positive_count > negative_count * 2:
            personality["情绪倾向"] = "积极乐观"
        elif negative_count > positive_count * 2:
            personality["情绪倾向"] = "相对消极"
        else:
            personality["情绪倾向"] = "情绪平稳"
            
        return personality
    
    def _analyze_communication_style(self, messages: List[str]) -> Dict[str, Any]:
        """分析沟通风格"""
        if not messages:
            return {"风格": "数据不足"}
            
        total_length = sum(len(msg) for msg in messages)
        avg_length = total_length / len(messages)
        
        emoji_count = sum(msg.count("😄") + msg.count("😊") + msg.count("😢") + 
                         msg.count("💪") + msg.count("😋") for msg in messages)
        
        style = {
            "消息长度": "简洁" if avg_length < 20 else "详细",
            "表情使用": "频繁" if emoji_count > len(messages) * 0.3 else "适中",
            "回复速度": "及时"  # 这里可以基于时间戳分析
        }
        
        return style
    
    def _extract_topics(self, messages: List[str]) -> List[str]:
        """提取常聊话题"""
        topics = []
        text = " ".join(messages)
        
        topic_keywords = {
            "工作": ["工作", "上班", "加班", "同事", "老板", "项目"],
            "生活": ["吃饭", "睡觉", "家里", "购物", "日常"],
            "学习": ["学习", "考试", "课程", "培训", "技能", "编程"],
            "感情": ["男朋友", "女朋友", "恋爱", "结婚", "分手"],
            "家庭": ["父母", "家人", "孩子", "亲戚"],
            "健康": ["身体", "医院", "生病", "锻炼", "健康", "健身"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in text for keyword in keywords):
                topics.append(topic)
                
        return topics
    
    def _save_user_profile(self, profile: UserProfile):
        """保存用户画像到数据库"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO user_profile 
            (user_id, interests, personality, communication_style, frequent_topics, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            self.user_id,
            json.dumps(profile.interests, ensure_ascii=False),
            json.dumps(profile.personality, ensure_ascii=False),
            json.dumps(profile.communication_style, ensure_ascii=False),
            json.dumps(profile.frequent_topics, ensure_ascii=False),
            datetime.now().isoformat()
        ))
        
        self.conn.commit()
    
    def get_personalized_response(self, question: str) -> str:
        """生成个性化回答"""
        # 获取用户画像
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT interests, personality, communication_style, frequent_topics
            FROM user_profile 
            WHERE user_id = ? 
            ORDER BY updated_at DESC 
            LIMIT 1
        """, (self.user_id,))
        
        result = cursor.fetchone()
        if not result:
            return "还没有足够的数据来了解你，请先导入一些聊天记录。"
        
        interests = json.loads(result[0])
        personality = json.loads(result[1])
        communication_style = json.loads(result[2])
        frequent_topics = json.loads(result[3])
        
        # 基于用户画像生成回答
        response = self._generate_response(question, interests, personality, communication_style, frequent_topics)
        
        return response
    
    def _generate_response(self, question: str, interests: List[str], 
                          personality: Dict[str, Any], communication_style: Dict[str, Any],
                          frequent_topics: List[str]) -> str:
        """基于用户画像生成回答"""
        
        # 简单的规则基回答生成
        response_parts = []
        
        # 根据问题类型和用户兴趣生成回答
        if "推荐" in question or "建议" in question:
            if "运动" in interests:
                response_parts.append("基于你平时喜欢运动，我建议你可以尝试一些新的运动项目，")
            if "美食" in interests:
                response_parts.append("考虑到你对美食的喜爱，我推荐一些健康美味的选择，")
            if "音乐" in interests:
                response_parts.append("结合你的音乐品味，我觉得你可能会喜欢，")
            if "电影" in interests:
                response_parts.append("根据你的观影喜好，我推荐，")
            if "科技" in interests:
                response_parts.append("基于你对科技的兴趣，我建议关注，")
        
        # 根据沟通风格调整回答方式
        if communication_style.get("消息长度") == "简洁":
            base_response = "简单来说："
        else:
            base_response = "让我详细为你分析一下："
        
        # 根据性格特征调整语气
        if personality.get("情绪倾向") == "积极乐观":
            tone = "😊 "
        else:
            tone = ""
        
        # 根据常聊话题调整回答内容
        if "健康" in frequent_topics and ("运动" in question or "锻炼" in question):
            response_parts.append("继续保持健康的生活方式很重要，")
        
        if not response_parts:
            response_parts.append("根据我对你的了解，我觉得")
        
        final_response = tone + base_response + " ".join(response_parts)
        
        # 如果回答太短，添加一些通用建议
        if len(final_response) < 50:
            final_response += "这只是我的个人建议，最终还是要根据你的实际情况来决定哦！"
        
        return final_response


def create_user(name: str, phone: str = "") -> Dict[str, Any]:
    """创建新用户"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO users (name, phone)
            VALUES (?, ?)
        """, (name, phone))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "user_id": user_id,
            "message": f"用户 {name} 创建成功，用户ID: {user_id}"
        }
        
    except sqlite3.Error as e:
        conn.close()
        return {
            "success": False,
            "error": str(e)
        }


def get_chat_stats(user_id: int) -> Dict[str, Any]:
    """获取聊天统计信息"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 统计总消息数
        cursor.execute("SELECT COUNT(*) FROM chat_records WHERE user_id = ?", (user_id,))
        total_messages = cursor.fetchone()[0]
        
        # 统计发送和接收的消息数
        cursor.execute("SELECT message_type, COUNT(*) FROM chat_records WHERE user_id = ? GROUP BY message_type", (user_id,))
        type_stats = dict(cursor.fetchall())
        
        # 统计联系人数量
        cursor.execute("SELECT COUNT(DISTINCT contact_name) FROM chat_records WHERE user_id = ? AND contact_name != ''", (user_id,))
        contact_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "success": True,
            "stats": {
                "total_messages": total_messages,
                "sent_messages": type_stats.get("sent", 0),
                "received_messages": type_stats.get("received", 0),
                "contact_count": contact_count
            }
        }
        
    except sqlite3.Error as e:
        return {
            "success": False,
            "error": f"统计失败: {str(e)}"
        }


def test_digital_twin():
    """测试数字分身功能"""
    
    print("🤖 数字分身功能测试")
    print("=" * 50)
    
    # 初始化数据库
    init_database()
    
    # 1. 创建用户
    print("\n1. 创建用户...")
    user_data = create_user("测试用户", "13800138000")
    print(f"创建结果: {user_data}")
    
    if not user_data["success"]:
        print("❌ 用户创建失败")
        return
    
    user_id = user_data["user_id"]
    print(f"✅ 用户创建成功，ID: {user_id}")
    
    # 2. 导入测试聊天记录
    print("\n2. 导入微信聊天记录...")
    test_messages = [
        ChatMessage(
            message_type="sent",
            content="今天去健身房锻炼了，感觉很棒！💪",
            timestamp="2024-01-15 18:30:00",
            contact_name="健身伙伴"
        ),
        ChatMessage(
            message_type="received",
            content="哇，坚持得真好！我也想去健身",
            timestamp="2024-01-15 18:31:00",
            contact_name="健身伙伴"
        ),
        ChatMessage(
            message_type="sent",
            content="一起啊！明天晚上7点，我们约个时间",
            timestamp="2024-01-15 18:32:00",
            contact_name="健身伙伴"
        ),
        ChatMessage(
            message_type="sent",
            content="昨天看了一部很棒的科幻电影，推荐给你",
            timestamp="2024-01-16 20:15:00",
            contact_name="电影爱好者"
        ),
        ChatMessage(
            message_type="received",
            content="什么电影？我最近正好想看电影",
            timestamp="2024-01-16 20:16:00",
            contact_name="电影爱好者"
        ),
        ChatMessage(
            message_type="sent",
            content="《流浪地球2》，特效和剧情都很赞！",
            timestamp="2024-01-16 20:17:00",
            contact_name="电影爱好者"
        ),
        ChatMessage(
            message_type="sent",
            content="今天做了红烧肉，味道不错😋",
            timestamp="2024-01-17 19:30:00",
            contact_name="美食分享群"
        ),
        ChatMessage(
            message_type="received",
            content="哇，看起来就很香！能分享一下菜谱吗？",
            timestamp="2024-01-17 19:31:00",
            contact_name="美食分享群"
        ),
        ChatMessage(
            message_type="sent",
            content="当然可以！我发个详细的制作过程给你",
            timestamp="2024-01-17 19:32:00",
            contact_name="美食分享群"
        ),
        ChatMessage(
            message_type="sent",
            content="最近在学Python编程，感觉很有趣",
            timestamp="2024-01-18 21:00:00",
            contact_name="技术交流群"
        )
    ]
    
    digital_twin = DigitalTwin(user_id)
    import_data = digital_twin.import_wechat_data(test_messages)
    print(f"导入结果: {import_data}")
    
    if not import_data["success"]:
        print("❌ 消息导入失败")
        return
    
    print(f"✅ 成功导入 {import_data['imported_count']} 条消息")
    
    # 3. 获取聊天统计
    print("\n3. 获取聊天统计...")
    stats_data = get_chat_stats(user_id)
    print(f"统计信息: {json.dumps(stats_data, ensure_ascii=False, indent=2)}")
    
    # 4. 分析用户画像
    print("\n4. 分析用户画像...")
    profile = digital_twin.analyze_user_profile()
    print(f"用户画像: {json.dumps(asdict(profile), ensure_ascii=False, indent=2)}")
    print("✅ 用户画像分析完成")
    
    # 5. 测试个性化问答
    print("\n5. 测试个性化问答...")
    
    test_questions = [
        "推荐一些适合我的运动",
        "我想看电影，有什么建议吗？",
        "今天想做什么菜比较好？",
        "我应该学习什么新技能？"
    ]
    
    for question in test_questions:
        print(f"\n❓ 问题: {question}")
        response = digital_twin.get_personalized_response(question)
        print(f"🤖 回答: {response}")
    
    print("\n" + "=" * 50)
    print("🎉 测试完成！数字分身已经可以根据你的聊天记录提供个性化建议了。")


if __name__ == "__main__":
    test_digital_twin()
