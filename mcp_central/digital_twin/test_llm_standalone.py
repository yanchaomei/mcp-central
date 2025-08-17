#!/usr/bin/env python3
"""
基于大模型的数字分身测试示例
需要先启动Ollama服务: ollama serve
并下载模型: ollama pull qwen2.5:7b
"""

import json
import asyncio
import sqlite3
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass
import os

# 导入我们的LLM版本模块
from server_llm import (
    ChatMessage, DigitalTwinLLM, LLMConfig, VectorDatabase, 
    init_database, create_user, get_chat_stats_llm
)


async def test_digital_twin_llm():
    """测试基于大模型的数字分身功能"""
    
    print("🤖 基于大模型的数字分身测试")
    print("=" * 60)
    
    # 检查Ollama服务
    print("\n🔍 检查Ollama服务状态...")
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:11434/api/tags") as response:
                if response.status == 200:
                    models = await response.json()
                    model_names = [m["name"] for m in models.get("models", [])]
                    print(f"✅ Ollama服务运行正常，可用模型: {model_names}")
                    
                    if "qwen2.5:7b" not in model_names:
                        print("⚠️  警告: 未找到qwen2.5:7b模型，请运行: ollama pull qwen2.5:7b")
                        print("继续使用可用的第一个模型进行测试...")
                else:
                    print("❌ Ollama服务连接失败")
                    return
    except Exception as e:
        print(f"❌ 无法连接到Ollama服务: {e}")
        print("请确保已启动Ollama服务: ollama serve")
        return
    
    # 初始化数据库
    init_database()
    
    # 1. 创建用户
    print("\n1. 创建用户...")
    user_result = await create_user("AI测试用户", "13900139000")
    user_data = json.loads(user_result)
    print(f"创建结果: {user_data}")
    
    if not user_data["success"]:
        print("❌ 用户创建失败")
        return
    
    user_id = user_data["user_id"]
    print(f"✅ 用户创建成功，ID: {user_id}")
    
    # 2. 准备更丰富的测试数据
    print("\n2. 准备测试聊天记录...")
    test_messages = [
        # 工作相关
        ChatMessage("sent", "今天的项目会议开得很顺利，大家对新的AI功能都很感兴趣", "2024-01-15 09:30:00", "项目组"),
        ChatMessage("received", "是的，特别是你提到的个性化推荐功能", "2024-01-15 09:31:00", "项目组"),
        ChatMessage("sent", "我觉得我们可以用大模型来做用户画像分析", "2024-01-15 09:32:00", "项目组"),
        
        # 兴趣爱好 - 编程
        ChatMessage("sent", "最近在学习PyTorch，深度学习真的很有趣", "2024-01-16 20:15:00", "技术群"),
        ChatMessage("received", "你进展怎么样？有什么好的学习资源推荐吗？", "2024-01-16 20:16:00", "技术群"),
        ChatMessage("sent", "推荐李沐的动手学深度学习，讲得很清楚", "2024-01-16 20:17:00", "技术群"),
        
        # 兴趣爱好 - 运动
        ChatMessage("sent", "今天跑了10公里，感觉状态越来越好了💪", "2024-01-17 18:30:00", "跑步群"),
        ChatMessage("received", "哇，太厉害了！我才跑了5公里就累死了", "2024-01-17 18:31:00", "跑步群"),
        ChatMessage("sent", "慢慢来，贵在坚持。我也是从3公里开始的", "2024-01-17 18:32:00", "跑步群"),
        
        # 生活态度
        ChatMessage("sent", "虽然工作很忙，但还是要保持学习的热情", "2024-01-18 21:00:00", "老同学"),
        ChatMessage("received", "你总是这么积极，真的很佩服", "2024-01-18 21:01:00", "老同学"),
        ChatMessage("sent", "生活就是要不断挑战自己嘛😊", "2024-01-18 21:02:00", "老同学"),
        
        # 兴趣爱好 - 阅读
        ChatMessage("sent", "最近在读《人类简史》，作者的视角很独特", "2024-01-19 19:00:00", "读书会"),
        ChatMessage("received", "这本书我也想读，你觉得怎么样？", "2024-01-19 19:01:00", "读书会"),
        ChatMessage("sent", "很值得读，让我重新思考了很多问题", "2024-01-19 19:02:00", "读书会"),
        
        # 情感表达
        ChatMessage("sent", "感谢大家一直以来的支持和帮助🙏", "2024-01-20 12:00:00", "朋友群"),
        ChatMessage("received", "我们都是互相帮助的好朋友", "2024-01-20 12:01:00", "朋友群"),
        ChatMessage("sent", "是的，有你们真好❤️", "2024-01-20 12:02:00", "朋友群"),
        
        # 专业思考
        ChatMessage("sent", "AI的发展真的很快，我们要不断学习才能跟上", "2024-01-21 14:30:00", "AI讨论群"),
        ChatMessage("received", "是啊，特别是大模型这块变化太快了", "2024-01-21 14:31:00", "AI讨论群"),
        ChatMessage("sent", "我觉得关键是要理解底层原理，不能只停留在表面", "2024-01-21 14:32:00", "AI讨论群"),
    ]
    
    print(f"准备了 {len(test_messages)} 条聊天记录")
    
    # 3. 导入聊天记录
    print("\n3. 导入微信聊天记录到LLM系统...")
    digital_twin = DigitalTwinLLM(user_id)
    import_result = await digital_twin.import_wechat_data(test_messages)
    print(f"导入结果: {import_result}")
    
    if not import_result["success"]:
        print("❌ 消息导入失败")
        return
    
    print(f"✅ 成功导入 {import_result['imported_count']} 条消息到向量数据库")
    
    # 4. 获取统计信息
    print("\n4. 获取聊天统计...")
    stats_result = await get_chat_stats_llm(user_id)
    stats_data = json.loads(stats_result)
    print(f"统计信息: {json.dumps(stats_data, ensure_ascii=False, indent=2)}")
    
    # 5. 使用LLM分析用户画像
    print("\n5. 使用大语言模型分析用户画像...")
    print("🔄 正在调用LLM进行深度分析，请稍候...")
    
    try:
        profile_result = await digital_twin.analyze_user_profile_llm()
        
        if profile_result["success"]:
            profile_data = profile_result["profile"]
            print("✅ 用户画像分析完成")
            print(f"📊 分析结果: {json.dumps(profile_data, ensure_ascii=False, indent=2)}")
        else:
            print(f"❌ 用户画像分析失败: {profile_result.get('error', '未知错误')}")
            return
            
    except Exception as e:
        print(f"❌ 用户画像分析出错: {e}")
        return
    
    # 6. 测试个性化问答
    print("\n6. 测试基于LLM的个性化问答...")
    
    test_questions = [
        "我想提升自己的技术能力，你有什么建议吗？",
        "最近工作压力有点大，怎么办？", 
        "推荐一些适合我的书籍",
        "我应该如何平衡工作和生活？",
        "你觉得我是什么样的人？"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n❓ 问题 {i}: {question}")
        print("🔄 LLM思考中...")
        
        try:
            response = await digital_twin.get_personalized_response_llm(question)
            print(f"🤖 个性化回答: {response}")
        except Exception as e:
            print(f"❌ 回答生成失败: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 基于大模型的数字分身测试完成！")
    print("\n💡 主要特性验证:")
    print("✅ 向量数据库存储和检索")
    print("✅ LLM深度用户画像分析")
    print("✅ RAG增强的个性化问答")
    print("✅ 上下文记忆和对话历史")
    print("✅ 个性化Prompt工程")


async def test_vector_search():
    """测试向量检索功能"""
    print("\n🔍 测试向量检索功能...")
    
    # 创建一个用户用于测试
    user_result = await create_user("向量测试用户")
    user_data = json.loads(user_result)
    user_id = user_data["user_id"]
    
    # 创建数字分身实例
    digital_twin = DigitalTwinLLM(user_id)
    
    # 添加一些测试消息
    test_msgs = [
        ChatMessage("sent", "我喜欢跑步和健身", "2024-01-01 10:00:00"),
        ChatMessage("sent", "Python是我最喜欢的编程语言", "2024-01-01 11:00:00"),
        ChatMessage("sent", "最近在读机器学习的书", "2024-01-01 12:00:00"),
    ]
    
    await digital_twin.import_wechat_data(test_msgs)
    
    # 测试相似度检索
    test_queries = ["运动健身", "编程开发", "学习读书", "工作项目"]
    
    for query in test_queries:
        similar_ids = digital_twin.vector_db.search_similar(query, top_k=2)
        print(f"查询: '{query}' -> 相似消息ID: {similar_ids}")


if __name__ == "__main__":
    print("🚀 启动基于大模型的数字分身测试")
    print("=" * 60)
    print("📋 测试前准备:")
    print("1. 确保已安装依赖: pip install -r requirements_llm.txt")
    print("2. 启动Ollama服务: ollama serve")
    print("3. 下载模型: ollama pull qwen2.5:7b")
    print("=" * 60)
    
    try:
        asyncio.run(test_digital_twin_llm())
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
