# Digital Twin MCP

这是一个数字分身MCP服务器，可以作为手机用户的私人助手，支持导入微信聊天记录并提供个性化问答服务。

## 功能特性

1. **微信聊天记录导入**: 支持导入微信聊天记录，包括发送和接收的消息
2. **用户画像分析**: 基于聊天记录自动分析用户的兴趣爱好、性格特征、沟通风格等
3. **个性化问答**: 根据用户画像提供个性化的回答和建议
4. **数据统计**: 提供聊天记录的统计信息

## 安装

```bash
pip install -r requirements.txt
```

## MCP 配置

```json
{
  "mcpServers": {
    "digital_twin": {
      "command": "/path/to/fastmcp",
      "args": [
        "run",
        "/path/to/mcp-central/mcp_central/digital_twin/server.py"
      ]
    }
  }
}
```

将此配置添加到你的聊天机器人或智能体配置文件中以使用数字分身MCP服务器。

## 功能说明

### 1. create_user
创建新用户并返回用户ID。

**输入参数:**
- `name` (string): 用户姓名
- `phone` (string, 可选): 用户手机号

**输出:**
```json
{
  "success": true,
  "user_id": 1,
  "message": "用户张三创建成功，用户ID: 1"
}
```

### 2. import_wechat_messages
导入微信聊天记录。

**输入参数:**
- `user_id` (int): 用户ID
- `messages_json` (string): JSON格式的消息数组

消息格式示例:
```json
[
  {
    "message_type": "sent",
    "content": "今天天气真不错",
    "timestamp": "2024-01-15 10:30:00",
    "contact_name": "小明"
  },
  {
    "message_type": "received", 
    "content": "是啊，适合出去走走",
    "timestamp": "2024-01-15 10:31:00",
    "contact_name": "小明"
  }
]
```

**输出:**
```json
{
  "imported_count": 2,
  "total_messages": 2,
  "success": true
}
```

### 3. analyze_user
基于已导入的聊天记录分析用户画像。

**输入参数:**
- `user_id` (int): 用户ID

**输出:**
```json
{
  "success": true,
  "profile": {
    "interests": ["运动", "音乐", "美食"],
    "personality": {
      "活跃度": "中等",
      "幽默感": "一般", 
      "表达方式": "直接",
      "情绪倾向": "积极乐观"
    },
    "communication_style": {
      "消息长度": "简洁",
      "表情使用": "适中",
      "回复速度": "及时"
    },
    "frequent_topics": ["工作", "生活", "运动"]
  }
}
```

### 4. personalized_qa
基于用户画像提供个性化问答。

**输入参数:**
- `user_id` (int): 用户ID
- `question` (string): 用户问题

**输出:**
```json
{
  "success": true,
  "response": "😊 简单来说：基于你平时喜欢运动，我建议你可以尝试一些户外活动..."
}
```

### 5. get_chat_stats
获取用户的聊天记录统计信息。

**输入参数:**
- `user_id` (int): 用户ID

**输出:**
```json
{
  "success": true,
  "stats": {
    "total_messages": 150,
    "sent_messages": 75,
    "received_messages": 75,
    "contact_count": 12
  }
}
```

## 数据存储

系统使用SQLite数据库存储数据，包含以下表：

- `users`: 用户基本信息
- `chat_records`: 聊天记录
- `user_profile`: 用户画像数据

数据库文件默认为 `digital_twin.db`，会在首次运行时自动创建。

## 使用示例

1. **创建用户**
```python
# 创建用户
result = await create_user("张三", "13800138000")
user_id = json.loads(result)["user_id"]
```

2. **导入聊天记录**
```python
# 准备聊天数据
messages = [
    {
        "message_type": "sent",
        "content": "今天去健身房了，感觉很棒！",
        "timestamp": "2024-01-15 18:30:00",
        "contact_name": "健身伙伴"
    },
    {
        "message_type": "received",
        "content": "哇，坚持得真好！",
        "timestamp": "2024-01-15 18:31:00", 
        "contact_name": "健身伙伴"
    }
]

# 导入数据
result = await import_wechat_messages(user_id, json.dumps(messages))
```

3. **分析用户画像**
```python
# 分析用户
profile = await analyze_user(user_id)
```

4. **个性化问答**
```python
# 提问
response = await personalized_qa(user_id, "推荐一些适合我的运动")
```

## 注意事项

1. 聊天记录中的时间戳格式应为 `YYYY-MM-DD HH:MM:SS`
2. 系统会自动分析中文文本，提取关键信息构建用户画像
3. 个性化回答基于简单的规则引擎，可以根据需要扩展更复杂的AI模型
4. 数据库文件包含敏感信息，请注意数据安全和隐私保护

## 扩展建议

1. **增强文本分析**: 集成更强大的NLP模型进行情感分析和主题提取
2. **多模态支持**: 支持图片、语音等多媒体消息分析
3. **个性化推荐**: 基于用户画像提供更精准的内容推荐
4. **隐私保护**: 添加数据加密和匿名化处理
5. **实时学习**: 支持基于用户反馈持续优化用户画像

## 许可证

本项目遵循项目根目录的LICENSE文件。
