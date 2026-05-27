Discord AI Study Bot
一个基于 discord.py 和 OpenAI 兼容接口构建的 AI 学习助手 Bot，支持在 Discord 中完成资料上传、基于资料问答、本地 RAG 检索、自动生成选择题、记录答题表现，以及根据错题给出复习建议。

这个项目适合用作：

AI + Discord Bot 的课程作业或作品集项目
RAG 入门练手项目
学习型社群的轻量知识问答机器人
后续扩展为“个性化学习助理”的基础版本
功能概览
/ask
向大模型提一个通用学习问题，获得简洁回答。
/upload_doc
上传 PDF、TXT、MD 学习资料到本地知识库。
/askdoc
基于已上传资料进行问答，并返回命中的来源信息。
/uploadstatus
查看当前上传目录和索引状态。
/list_docs
列出已收录的学习资料。
/quiz
根据已上传资料自动生成一道选择题。
/answer_quiz
提交当前题目的答案并获取解析。
/mystats
查看个人答题统计、正确率和薄弱来源。
/review
基于最近的答题记录生成简短复习建议。
项目亮点
使用 Discord Slash Commands，交互方式清晰，适合真实群聊场景
支持上传学习资料并建立本地知识库
使用本地 sentence-transformers 生成向量，降低嵌入成本
使用 OpenAI 兼容接口调用聊天模型，便于切换到 DeepSeek 等提供商
支持重复文件检测，避免重复索引相同内容
同名文件上传时会替换旧版本索引
问答和测验都尽量基于检索到的资料内容生成
会保存每位用户的答题记录，并据此识别薄弱资料来源
技术架构
整体流程分为 4 层：

Discord 交互层
由 bot/discord_client.py 对 Slash Commands 进行注册和响应。

LLM 能力层
services/llm_service.py 负责：

通用问答
基于上下文回答问题
生成文本向量
生成测验
生成复习建议
RAG 与数据处理层

services/ingest_service.py：处理文件上传、抽取文本、切块、生成向量、写入索引
services/retrieval_service.py：根据问题检索相似片段并拼接上下文
services/vector_store.py：基于 JSON 文件实现最简本地向量库
学习记录层

services/quiz_service.py：管理当前活跃题目
services/study_record_service.py：记录答题历史、统计正确率、生成复习上下文
RAG 工作流程
用户通过 /upload_doc 上传 PDF、TXT 或 MD 文件。
系统将文件保存到本地 data/uploads/。
文本被提取并清洗后按固定长度切块。
使用本地嵌入模型将每个文本块转换成向量。
文本块和向量一起写入 data/vector_store/index.json。
当用户执行 /askdoc 或 /quiz 时，系统会先检索最相关的片段。
检索结果被作为上下文传给聊天模型，生成回答或题目。
项目结构
discord_ai_study_bot/
├── app/
│   └── config.py                  # 环境变量读取与配置校验
├── bot/
│   └── discord_client.py          # Discord 客户端与 Slash Commands
├── data/
│   ├── quiz_sessions.json         # 当前活跃题目
│   ├── study_records.json         # 用户答题记录
│   ├── uploads/                   # 上传的原始资料
│   └── vector_store/
│       └── index.json             # 本地 JSON 向量索引
├── services/
│   ├── ingest_service.py          # 文档摄取与切块
│   ├── llm_service.py             # 模型调用与向量生成
│   ├── quiz_service.py            # 出题与会话管理
│   ├── retrieval_service.py       # 检索逻辑
│   ├── study_record_service.py    # 学习记录与统计
│   └── vector_store.py            # JSON 向量库
├── .gitignore
├── .env
├── main.py
└── requirements.txt
运行环境
Python 3.10+，推荐 3.11 或 3.12
一个已创建好的 Discord Bot
可用的 OpenAI 兼容聊天模型接口
首次运行时可联网下载嵌入模型
安装与启动
1. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate
Windows:

.venv\Scripts\activate
2. 安装依赖
pip install -r requirements.txt
3. 配置环境变量
在项目根目录创建 .env：

DISCORD_BOT_TOKEN=your_discord_bot_token
CHAT_API_KEY=your_model_api_key
CHAT_BASE_URL=https://api.deepseek.com
CHAT_MODEL=deepseek-v4-flash
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
BOT_PREFIX=!
说明：

DISCORD_BOT_TOKEN：Discord 机器人的 Token
CHAT_API_KEY：聊天模型服务提供商的 API Key
CHAT_BASE_URL：OpenAI 兼容接口地址
CHAT_MODEL：聊天模型名称
EMBEDDING_MODEL：本地嵌入模型名称
BOT_PREFIX：当前项目里主要使用 Slash Commands，这个前缀字段预留但实际作用很小
4. 启动机器人
python main.py
如果启动成功，控制台会输出类似：

Logged in as YourBotName (ID: xxxxxxxxxxxxx)
Discord 侧配置建议
在 Discord Developer Portal 中，建议至少开启和配置：

bot 权限
applications.commands scope
允许 Bot 所在频道使用 Slash Commands
允许上传附件，否则 /upload_doc 无法正常使用
这个项目默认关闭了 message_content intent，因为主要交互依赖 Slash Commands。

命令示例
1. 通用问答
/ask question: 什么是监督学习？
2. 上传学习资料
/upload_doc file: machine_learning_notes.pdf
3. 基于资料问答
/askdoc question: 这份资料里是怎么解释过拟合的？
4. 生成测验
/quiz topic: 神经网络基础
5. 回答测验
/answer_quiz choice: A
6. 查看学习统计
/mystats
7. 获取复习建议
/review
数据存储说明
当前版本采用本地文件存储，结构简单，便于理解和演示：

data/uploads/
保存原始上传文件
data/uploads/documents.json
保存文档元信息，例如文件名、哈希值、页数、切块数、上传时间
data/vector_store/index.json
保存切块文本和对应向量
data/quiz_sessions.json
保存每位用户当前尚未作答的题目
data/study_records.json
保存历史答题记录和统计基础数据
这意味着当前版本更适合作为本地开发、课程展示或小规模使用，不适合高并发生产环境。

已实现的细节设计
文档摄取
支持 PDF、TXT、MD
PDF 按页提取文本
文本会做空白字符清洗
使用固定窗口切块，并保留一定重叠
重复文件处理
基于文件 SHA-256 做重复检测
如果上传内容完全相同，会跳过重复索引
如果文件名相同但内容不同，会移除旧索引并替换为新版本
检索与回答
当前使用余弦相似度进行向量检索
默认返回 Top-K 相关片段
/askdoc 会将命中来源附在回答后面
学习闭环
/quiz 会优先参考历史上的薄弱来源出题
/answer_quiz 会记录答题正确与否、题目解析、来源
/mystats 会显示正确率和常错来源
/review 会根据近期错题给出下一步复习建议
局限性
当前版本是一个很不错的 MVP，但也有几个明显边界：

向量库是 JSON 文件，不适合大规模数据
没有权限隔离，不同用户共享同一个资料知识库
没有后台任务队列，大文件上传和嵌入会阻塞一段时间
PDF 文本抽取质量依赖原文件，扫描版 PDF 可能效果较差
没有数据库，所有状态都落在本地文件中
没有单元测试和部署脚本
后续可扩展方向
用 FAISS、Chroma 或 pgvector 替换 JSON 向量库
增加多文档标签、课程分类和按用户隔离知识库
支持更多文件格式，例如 docx、pptx
接入 OCR，提升扫描版 PDF 的可用性
增加 spaced repetition 或定时复习提醒
增加管理员命令，例如删除文档、重建索引、查看全局统计
为测验增加填空题、判断题和连续出题模式
补充测试、Dockerfile 和部署说明
适合写在简历或作品集里的描述
你可以这样概括这个项目：

开发了一个基于 Discord 的 AI 学习助手，支持本地 RAG 知识库问答、学习资料上传索引、自动生成测验、答题统计与个性化复习建议，使用 discord.py、sentence-transformers 和 OpenAI 兼容大模型接口完成端到端实现。

License
如果你准备公开发布项目，建议补充一个正式的开源许可证，例如 MIT License。
