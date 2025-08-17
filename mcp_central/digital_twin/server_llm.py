import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass
import numpy as np
import os

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    VECTOR_SUPPORT = True
except ImportError:
    VECTOR_SUPPORT = False
    print("警告: 未安装sentence_transformers或faiss，向量功能将不可用")

from fastmcp import FastMCP

mcp = FastMCP("digital_twin_llm")

# 数据库初始化
DB_PATH = "digital_twin_llm.db"
VECTOR_DB_PATH = "user_vectors.index"

class LLMConfig:
    """大模型配置"""
    def __init__(self):
        # 可以配置不同的模型
        self.model_name = "qwen2.5:7b"  # Ollama模型
        self.embedding_model = "all-MiniLM-L6-v2"  # 嵌入模型
        self.max_tokens = 2048
        self.temperature = 0.7
        self.api_base = "http://localhost:11434"  # Ollama默认地址


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
            message_type TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TIMESTAMP,
            contact_name TEXT,
            embedding_id INTEGER,  -- 对应向量数据库的ID
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # 创建用户画像表（LLM生成的结构化画像）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profile_llm (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            profile_json TEXT,  -- LLM生成的完整用户画像JSON
            personality_summary TEXT,  -- 性格总结
            interests_summary TEXT,    -- 兴趣总结
            communication_style TEXT,  -- 沟通风格
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # 创建对话历史表（用于上下文记忆）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT,
            answer TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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


class VectorDatabase:
    """向量数据库管理"""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # 内积相似度
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.message_mapping = {}  # ID到消息的映射
        
    def add_messages(self, messages: List[str], message_ids: List[int]):
        """添加消息到向量数据库"""
        embeddings = self.embedding_model.encode(messages)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)  # 归一化
        
        self.index.add(embeddings.astype('float32'))
        
        # 更新映射
        start_id = len(self.message_mapping)
        for i, msg_id in enumerate(message_ids):
            self.message_mapping[start_id + i] = msg_id
    
    def search_similar(self, query: str, top_k: int = 5) -> List[int]:
        """搜索相似消息"""
        query_embedding = self.embedding_model.encode([query])
        query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
        
        _, indices = self.index.search(query_embedding.astype('float32'), top_k)
        
        # 返回消息ID
        return [self.message_mapping.get(idx, -1) for idx in indices[0] if idx in self.message_mapping]
    
    def save(self, path: str):
        """保存向量数据库"""
        faiss.write_index(self.index, path)
        
    def load(self, path: str):
        """加载向量数据库"""
        if os.path.exists(path):
            self.index = faiss.read_index(path)


class LLMClient:
    """大语言模型客户端"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        
    async def generate_response(self, prompt: str) -> str:
        """生成回答"""
        try:
            import aiohttp
            
            payload = {
                "model": self.config.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.config.api_base}/api/generate", 
                                      json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response", "抱歉，无法生成回答。")
                    else:
                        return "模型服务暂时不可用，请稍后再试。"
                        
        except (aiohttp.ClientError, KeyError) as e:
            print(f"LLM调用失败: {e}")
            return "抱歉，生成回答时出现错误。"


class DigitalTwinLLM:
    """基于大模型的数字分身"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.conn = sqlite3.connect(DB_PATH)
        self.vector_db = VectorDatabase()
        self.llm_client = LLMClient(LLMConfig())
        
        # 尝试加载已有的向量数据库
        vector_path = f"{VECTOR_DB_PATH}_{user_id}"
        if os.path.exists(vector_path):
            self.vector_db.load(vector_path)
    
    def __del__(self):
        if hasattr(self, 'conn'):
            self.conn.close()
    
    async def import_wechat_data(self, messages: List[ChatMessage]) -> Dict[str, Any]:
        """导入微信聊天记录"""
        cursor = self.conn.cursor()
        imported_count = 0
        message_texts = []
        message_ids = []
        
        for msg in messages:
            try:
                cursor.execute("""
                    INSERT INTO chat_records (user_id, message_type, content, timestamp, contact_name)
                    VALUES (?, ?, ?, ?, ?)
                """, (self.user_id, msg.message_type, msg.content, msg.timestamp, msg.contact_name))
                
                msg_id = cursor.lastrowid
                message_texts.append(msg.content)
                message_ids.append(msg_id)
                imported_count += 1
                
            except sqlite3.Error as e:
                print(f"导入消息失败: {e}")
        
        # 添加到向量数据库
        if message_texts:
            self.vector_db.add_messages(message_texts, message_ids)
            # 保存向量数据库
            vector_path = f"{VECTOR_DB_PATH}_{self.user_id}"
            self.vector_db.save(vector_path)
        
        self.conn.commit()
        return {
            "imported_count": imported_count,
            "total_messages": len(messages),
            "success": True
        }
    
    async def analyze_user_profile_llm(self) -> Dict[str, Any]:
        """使用LLM分析用户画像"""
        cursor = self.conn.cursor()
        
        # 获取所有聊天记录
        cursor.execute("""
            SELECT message_type, content, contact_name, timestamp
            FROM chat_records 
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 100
        """, (self.user_id,))
        
        records = cursor.fetchall()
        
        if not records:
            return {"success": False, "error": "没有足够的聊天记录进行分析"}
        
        # 构建分析prompt
        chat_context = self._build_chat_context(records)
        analysis_prompt = self._build_analysis_prompt(chat_context)
        
        # 使用LLM进行分析
        profile_response = await self.llm_client.generate_response(analysis_prompt)
        
        try:
            # 尝试解析LLM返回的JSON格式画像
            profile_data = json.loads(profile_response)
        except json.JSONDecodeError:
            # 如果不是JSON格式，则包装成结构化数据
            profile_data = {
                "raw_analysis": profile_response,
                "interests": [],
                "personality": {},
                "communication_style": {},
                "summary": profile_response[:200] + "..." if len(profile_response) > 200 else profile_response
            }
        
        # 保存到数据库
        cursor.execute("""
            INSERT OR REPLACE INTO user_profile_llm 
            (user_id, profile_json, personality_summary, interests_summary, communication_style, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            self.user_id,
            json.dumps(profile_data, ensure_ascii=False),
            profile_data.get("personality_summary", ""),
            profile_data.get("interests_summary", ""),
            profile_data.get("communication_style", ""),
            datetime.now().isoformat()
        ))
        
        self.conn.commit()
        
        return {
            "success": True,
            "profile": profile_data
        }
    
    def _build_chat_context(self, records: List[tuple]) -> str:
        """构建聊天上下文"""
        context_lines = []
        for record in records[:50]:  # 限制上下文长度
            msg_type, content, contact, timestamp = record
            direction = "我说" if msg_type == "sent" else f"{contact}说"
            context_lines.append(f"{timestamp} {direction}: {content}")
        
        return "\n".join(context_lines)
    
    def _build_analysis_prompt(self, chat_context: str) -> str:
        """构建用户画像分析的prompt"""
        return f"""
你是一个专业的用户画像分析师。请根据以下聊天记录，深入分析用户的特征，并以JSON格式返回分析结果。

聊天记录：
{chat_context}

请分析以下方面并以JSON格式返回：
{{
    "interests": ["兴趣1", "兴趣2", ...],
    "personality": {{
        "性格特点": "描述",
        "情绪倾向": "积极/消极/中性",
        "社交风格": "外向/内向/中性"
    }},
    "communication_style": {{
        "表达方式": "直接/委婉/幽默",
        "语言风格": "正式/随意/活泼",
        "回复习惯": "及时/延迟/不定"
    }},
    "values_and_attitudes": {{
        "价值观": "描述主要价值观",
        "生活态度": "积极/消极/平和"
    }},
    "behavioral_patterns": ["行为模式1", "行为模式2", ...],
    "personality_summary": "用一段话总结用户的整体性格特征",
    "interests_summary": "用一段话总结用户的主要兴趣爱好",
    "communication_style_summary": "用一段话总结用户的沟通风格"
}}

要求：
1. 基于聊天内容的具体分析，不要泛泛而谈
2. 注意识别用户的真实情感和态度
3. 分析要客观、准确、有依据
4. 返回标准的JSON格式
"""
    
    async def get_personalized_response_llm(self, question: str) -> str:
        """基于LLM和RAG生成个性化回答"""
        # 1. 获取用户画像
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT profile_json FROM user_profile_llm 
            WHERE user_id = ? 
            ORDER BY updated_at DESC 
            LIMIT 1
        """, (self.user_id,))
        
        result = cursor.fetchone()
        if not result:
            return "还没有分析过你的用户画像，请先导入聊天记录并进行分析。"
        
        user_profile = json.loads(result[0])
        
        # 2. 检索相关的历史对话
        similar_msg_ids = self.vector_db.search_similar(question, top_k=3)
        relevant_context = ""
        
        if similar_msg_ids:
            placeholders = ','.join('?' * len(similar_msg_ids))
            cursor.execute(f"""
                SELECT content, message_type, contact_name 
                FROM chat_records 
                WHERE id IN ({placeholders})
            """, similar_msg_ids)
            
            relevant_records = cursor.fetchall()
            context_lines = []
            for content, msg_type, contact in relevant_records:
                direction = "我" if msg_type == "sent" else contact
                context_lines.append(f"{direction}: {content}")
            
            relevant_context = "\n".join(context_lines)
        
        # 3. 获取最近的对话历史
        cursor.execute("""
            SELECT question, answer FROM conversation_history 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 3
        """, (self.user_id,))
        
        recent_conversations = cursor.fetchall()
        conversation_history = ""
        for q, a in recent_conversations:
            conversation_history += f"Q: {q}\nA: {a}\n\n"
        
        # 4. 构建个性化prompt
        personalized_prompt = self._build_personalized_prompt(
            question, user_profile, relevant_context, conversation_history
        )
        
        # 5. 生成回答
        response = await self.llm_client.generate_response(personalized_prompt)
        
        # 6. 保存对话历史
        cursor.execute("""
            INSERT INTO conversation_history (user_id, question, answer)
            VALUES (?, ?, ?)
        """, (self.user_id, question, response))
        
        self.conn.commit()
        
        return response
    
    def _build_personalized_prompt(self, question: str, user_profile: Dict[str, Any], 
                                 relevant_context: str, conversation_history: str) -> str:
        """构建个性化回答的prompt"""
        
        personality_summary = user_profile.get("personality_summary", "")
        interests_summary = user_profile.get("interests_summary", "")
        communication_style = user_profile.get("communication_style_summary", "")
        
        prompt = f"""
你是用户的个人AI助手，需要根据用户的个性特征提供个性化的回答。

用户画像：
性格特征：{personality_summary}
兴趣爱好：{interests_summary}
沟通风格：{communication_style}

相关历史对话片段：
{relevant_context}

最近对话历史：
{conversation_history}

用户问题：{question}

请基于用户的个性特征，用符合用户沟通风格的方式回答问题。要求：
1. 回答要体现对用户个性的理解
2. 语气和表达方式要符合用户的沟通习惯
3. 结合用户的兴趣爱好给出相关建议
4. 保持回答的自然和贴心
5. 如果有相关的历史对话，可以适当参考
"""
        
        return prompt


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


@mcp.tool(description="导入微信聊天记录，使用LLM进行智能分析")
async def import_wechat_messages_llm(user_id: int, messages_json: str) -> str:
    """导入微信聊天记录（LLM版本）"""
    try:
        messages_data = json.loads(messages_json)
        messages = [ChatMessage(**msg) for msg in messages_data]
        
        digital_twin = DigitalTwinLLM(user_id)
        result = await digital_twin.import_wechat_data(messages)
        
        return json.dumps(result, ensure_ascii=False)
        
    except (json.JSONDecodeError, TypeError, sqlite3.Error) as e:
        return json.dumps({
            "success": False,
            "error": f"导入失败: {str(e)}"
        }, ensure_ascii=False)


@mcp.tool(description="使用大语言模型分析用户画像")
async def analyze_user_llm(user_id: int) -> str:
    """使用LLM分析用户画像"""
    try:
        digital_twin = DigitalTwinLLM(user_id)
        result = await digital_twin.analyze_user_profile_llm()
        
        return json.dumps(result, ensure_ascii=False)
        
    except sqlite3.Error as e:
        return json.dumps({
            "success": False,
            "error": f"分析失败: {str(e)}"
        }, ensure_ascii=False)


@mcp.tool(description="基于大语言模型和RAG提供个性化问答")
async def personalized_qa_llm(user_id: int, question: str) -> str:
    """基于LLM的个性化问答"""
    try:
        digital_twin = DigitalTwinLLM(user_id)
        response = await digital_twin.get_personalized_response_llm(question)
        
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
async def get_chat_stats_llm(user_id: int) -> str:
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
        
        # 获取用户画像更新时间
        cursor.execute("SELECT updated_at FROM user_profile_llm WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1", (user_id,))
        profile_result = cursor.fetchone()
        profile_updated = profile_result[0] if profile_result else None
        
        conn.close()
        
        return json.dumps({
            "success": True,
            "stats": {
                "total_messages": total_messages,
                "sent_messages": type_stats.get("sent", 0),
                "received_messages": type_stats.get("received", 0),
                "contact_count": contact_count,
                "profile_last_updated": profile_updated
            }
        }, ensure_ascii=False)
        
    except sqlite3.Error as e:
        return json.dumps({
            "success": False,
            "error": f"统计失败: {str(e)}"
        }, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
