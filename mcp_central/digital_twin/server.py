import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

from fastmcp import FastMCP

mcp = FastMCP("digital_twin")

# 数据库初始化
DB_PATH = "digital_twin.db"


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
                         msg.count("👍") + msg.count("❤️") for msg in messages)
        
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
            "学习": ["学习", "考试", "课程", "培训", "技能"],
            "感情": ["男朋友", "女朋友", "恋爱", "结婚", "分手"],
            "家庭": ["父母", "家人", "孩子", "亲戚"],
            "健康": ["身体", "医院", "生病", "锻炼", "健康"]
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
                          _frequent_topics: List[str]) -> str:
        """基于用户画像生成回答"""
        
        # 简单的规则基回答生成
        response_parts = []
        
        # 根据问题类型和用户兴趣生成回答
        if "推荐" in question or "建议" in question:
            if "运动" in interests:
                response_parts.append("基于你平时喜欢运动，我建议...")
            if "美食" in interests:
                response_parts.append("考虑到你对美食的喜爱...")
            if "音乐" in interests:
                response_parts.append("结合你的音乐品味...")
        
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
        
        if not response_parts:
            response_parts.append("根据我对你的了解，我觉得...")
        
        final_response = tone + base_response + " ".join(response_parts)
        
        # 如果回答太短，添加一些通用建议
        if len(final_response) < 50:
            final_response += "不过这只是我的个人建议，最终还是要根据你的实际情况来决定哦！"
        
        return final_response


# 初始化数据库
init_database()


@mcp.tool(description="创建新用户并返回用户ID")
async def create_user(name: str, phone: str = "") -> str:
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
        
        return json.dumps({
            "success": True,
            "user_id": user_id,
            "message": f"用户 {name} 创建成功，用户ID: {user_id}"
        }, ensure_ascii=False)
        
    except sqlite3.Error as e:
        conn.close()
        return json.dumps({
            "success": False,
            "error": str(e)
        }, ensure_ascii=False)


@mcp.tool(description="导入微信聊天记录。messages格式为JSON数组，每个元素包含message_type('sent'或'received')、content、timestamp、contact_name字段")
async def import_wechat_messages(user_id: int, messages_json: str) -> str:
    """导入微信聊天记录"""
    try:
        messages_data = json.loads(messages_json)
        messages = [ChatMessage(**msg) for msg in messages_data]
        
        digital_twin = DigitalTwin(user_id)
        result = digital_twin.import_wechat_data(messages)
        
        return json.dumps(result, ensure_ascii=False)
        
    except (json.JSONDecodeError, TypeError, sqlite3.Error) as e:
        return json.dumps({
            "success": False,
            "error": f"导入失败: {str(e)}"
        }, ensure_ascii=False)


@mcp.tool(description="分析用户画像，基于已导入的聊天记录")
async def analyze_user(user_id: int) -> str:
    """分析用户画像"""
    try:
        digital_twin = DigitalTwin(user_id)
        profile = digital_twin.analyze_user_profile()
        
        return json.dumps({
            "success": True,
            "profile": asdict(profile)
        }, ensure_ascii=False)
        
    except sqlite3.Error as e:
        return json.dumps({
            "success": False,
            "error": f"分析失败: {str(e)}"
        }, ensure_ascii=False)


@mcp.tool(description="基于用户画像提供个性化问答")
async def personalized_qa(user_id: int, question: str) -> str:
    """个性化问答"""
    try:
        digital_twin = DigitalTwin(user_id)
        response = digital_twin.get_personalized_response(question)
        
        return json.dumps({
            "success": True,
            "response": response
        }, ensure_ascii=False)
        
    except (sqlite3.Error, json.JSONDecodeError) as e:
        return json.dumps({
            "success": False,
            "error": f"回答生成失败: {str(e)}"
        }, ensure_ascii=False)


@mcp.tool(description="获取用户的聊天记录统计信息")
async def get_chat_stats(user_id: int) -> str:
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
        
        return json.dumps({
            "success": True,
            "stats": {
                "total_messages": total_messages,
                "sent_messages": type_stats.get("sent", 0),
                "received_messages": type_stats.get("received", 0),
                "contact_count": contact_count
            }
        }, ensure_ascii=False)
        
    except sqlite3.Error as e:
        return json.dumps({
            "success": False,
            "error": f"统计失败: {str(e)}"
        }, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
