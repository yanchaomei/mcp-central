#!/usr/bin/env python3
"""
数字分身MCP服务器测试示例
演示如何使用各种功能
"""

import json
import asyncio
from server import create_user, import_wechat_messages, analyze_user, personalized_qa, get_chat_stats


async def test_digital_twin():
    """测试数字分身功能"""
    
    print("🤖 数字分身MCP服务器测试")
    print("=" * 50)
    
    # 1. 创建用户
    print("\n1. 创建用户...")
    user_result = await create_user("测试用户", "13800138000")
    user_data = json.loads(user_result)
    print(f"创建结果: {user_data}")
    
    if not user_data["success"]:
        print("❌ 用户创建失败")
        return
    
    user_id = user_data["user_id"]
    print(f"✅ 用户创建成功，ID: {user_id}")
    
    # 2. 导入测试聊天记录
    print("\n2. 导入微信聊天记录...")
    test_messages = [
        {
            "message_type": "sent",
            "content": "今天去健身房锻炼了，感觉很棒！💪",
            "timestamp": "2024-01-15 18:30:00",
            "contact_name": "健身伙伴"
        },
        {
            "message_type": "received",
            "content": "哇，坚持得真好！我也想去健身",
            "timestamp": "2024-01-15 18:31:00",
            "contact_name": "健身伙伴"
        },
        {
            "message_type": "sent",
            "content": "一起啊！明天晚上7点，我们约个时间",
            "timestamp": "2024-01-15 18:32:00",
            "contact_name": "健身伙伴"
        },
        {
            "message_type": "sent",
            "content": "昨天看了一部很棒的科幻电影，推荐给你",
            "timestamp": "2024-01-16 20:15:00",
            "contact_name": "电影爱好者"
        },
        {
            "message_type": "received",
            "content": "什么电影？我最近正好想看电影",
            "timestamp": "2024-01-16 20:16:00",
            "contact_name": "电影爱好者"
        },
        {
            "message_type": "sent",
            "content": "《流浪地球2》，特效和剧情都很赞！",
            "timestamp": "2024-01-16 20:17:00",
            "contact_name": "电影爱好者"
        },
        {
            "message_type": "sent",
            "content": "今天做了红烧肉，味道不错😋",
            "timestamp": "2024-01-17 19:30:00",
            "contact_name": "美食分享群"
        },
        {
            "message_type": "received",
            "content": "哇，看起来就很香！能分享一下菜谱吗？",
            "timestamp": "2024-01-17 19:31:00",
            "contact_name": "美食分享群"
        },
        {
            "message_type": "sent",
            "content": "当然可以！我发个详细的制作过程给你",
            "timestamp": "2024-01-17 19:32:00",
            "contact_name": "美食分享群"
        },
        {
            "message_type": "sent",
            "content": "最近在学Python编程，感觉很有趣",
            "timestamp": "2024-01-18 21:00:00",
            "contact_name": "技术交流群"
        }
    ]
    
    import_result = await import_wechat_messages(user_id, json.dumps(test_messages))
    import_data = json.loads(import_result)
    print(f"导入结果: {import_data}")
    
    if not import_data["success"]:
        print("❌ 消息导入失败")
        return
    
    print(f"✅ 成功导入 {import_data['imported_count']} 条消息")
    
    # 3. 获取聊天统计
    print("\n3. 获取聊天统计...")
    stats_result = await get_chat_stats(user_id)
    stats_data = json.loads(stats_result)
    print(f"统计信息: {json.dumps(stats_data, ensure_ascii=False, indent=2)}")
    
    # 4. 分析用户画像
    print("\n4. 分析用户画像...")
    profile_result = await analyze_user(user_id)
    profile_data = json.loads(profile_result)
    print(f"用户画像: {json.dumps(profile_data, ensure_ascii=False, indent=2)}")
    
    if not profile_data["success"]:
        print("❌ 用户画像分析失败")
        return
    
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
        qa_result = await personalized_qa(user_id, question)
        qa_data = json.loads(qa_result)
        
        if qa_data["success"]:
            print(f"🤖 回答: {qa_data['response']}")
        else:
            print(f"❌ 回答失败: {qa_data['error']}")
    
    print("\n" + "=" * 50)
    print("🎉 测试完成！数字分身已经可以根据你的聊天记录提供个性化建议了。")


if __name__ == "__main__":
    asyncio.run(test_digital_twin())
