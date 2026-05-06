---
name: langchain
description: "使用 LangChain 和 LangGraph 构建 LLM 应用。适用于创建 RAG 管道、Agent 工作流、链式调用或复杂的 LLM 编排。触发关键词：LangChain, LangGraph, LCEL, RAG, retrieval, agent chain, 大语言模型。"
---

# LangChain 与 LangGraph

使用可组合的链和智能体图构建复杂的 LLM 应用。LangChain 是一个用于开发大语言模型驱动应用的框架，提供构建复杂 LLM 工作流的工具和接口。

## 快速开始

```bash
pip install -U langchain langchain-openai langchain-anthropic langgraph langchain-community langchain-text-splitters
```

```python
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

# --------------------------------------------------------------------------------
# 简单链：创建提示模板并与模型组合
# --------------------------------------------------------------------------------
llm = ChatAnthropic(model="claude-3-sonnet-20240229")
prompt = ChatPromptTemplate.from_template("用简单的话解释{topic}。")
chain = prompt | llm

response = chain.invoke({"topic": "量子计算"})
```

## LCEL（LangChain 表达式语言）

使用管道操作符组合链：

```python
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# --------------------------------------------------------------------------------
# 带解析的链：组合输入、提示、模型和输出解析器
# --------------------------------------------------------------------------------
chain = (
    {"topic": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

result = chain.invoke("机器学习")
```

## RAG 管道（检索增强生成）

```python
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

# --------------------------------------------------------------------------------
# 创建向量存储：将文档转换为向量并存储
# --------------------------------------------------------------------------------
embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(documents, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

# RAG 提示模板
prompt = ChatPromptTemplate.from_template("""
根据以下上下文回答问题：
{context}

问题：{question}
""")

# --------------------------------------------------------------------------------
# RAG 链：检索相关文档并生成答案
# --------------------------------------------------------------------------------
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

answer = rag_chain.invoke("退款政策是什么？")
```

## LangGraph 智能体

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from typing import TypedDict, Annotated
import operator

# --------------------------------------------------------------------------------
# 定义状态：智能体的消息历史
# --------------------------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]

# --------------------------------------------------------------------------------
# 定义工具：智能体可以调用的功能
# --------------------------------------------------------------------------------
@tool
def search(query: str) -> str:
    """搜索网络。"""
    return f"搜索结果：{query}"

@tool
def calculator(expression: str) -> str:
    """计算数学表达式。"""
    return str(eval(expression))

tools = [search, calculator]

# --------------------------------------------------------------------------------
# 创建图：定义智能体的工作流
# --------------------------------------------------------------------------------
graph = StateGraph(AgentState)

# 添加节点
graph.add_node("agent", call_model)
graph.add_node("tools", ToolNode(tools))

# 添加边
graph.set_entry_point("agent")
graph.add_conditional_edges(
    "agent",
    should_continue,
    {"continue": "tools", "end": END}
)
graph.add_edge("tools", "agent")

# 编译图
app = graph.compile()

# 运行
result = app.invoke({"messages": [HumanMessage(content="25 乘以 4 等于多少？")]})
```

## RAG 智能体（使用 create_agent）

```python
import bs4
from langchain.agents import create_agent
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.tools import tool

# --------------------------------------------------------------------------------
# 加载和分块网页内容
# --------------------------------------------------------------------------------
loader = WebBaseLoader(
    web_paths=("https://example.com/docs",),
    bs_kwargs=dict(parse_only=bs4.SoupStrainer(class_=("post-content",)))
)
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
all_splits = text_splitter.split_documents(docs)

# 索引分块
vector_store.add_documents(documents=all_splits)

# --------------------------------------------------------------------------------
# 构建检索工具
# --------------------------------------------------------------------------------
@tool(response_format="content_and_artifact")
def retrieve_context(query: str):
    """检索信息以帮助回答问题。"""
    retrieved_docs = vector_store.similarity_search(query, k=2)
    serialized = "\n\n".join(
        f"来源: {doc.metadata}\n内容: {doc.page_content}"
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs

tools = [retrieve_context]

# 创建智能体
agent = create_agent(
    model,
    tools,
    system_prompt="你可以使用检索工具从文档中获取上下文信息。"
)
```

## 结构化输出

```python
from langchain_core.pydantic_v1 import BaseModel, Field

# --------------------------------------------------------------------------------
# 定义输出结构：Pydantic 模型
# --------------------------------------------------------------------------------
class Person(BaseModel):
    name: str = Field(description="人物姓名")
    age: int = Field(description="人物年龄")
    occupation: str = Field(description="人物职业")

# 结构化 LLM
structured_llm = llm.with_structured_output(Person)

result = structured_llm.invoke("张三是一位30岁的工程师")
# Person(name='张三', age=30, occupation='工程师')
```

## 记忆功能

```python
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# --------------------------------------------------------------------------------
# 消息历史存储
# --------------------------------------------------------------------------------
store = {}

def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# 带记忆的链
with_memory = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history"
)

# 使用会话
response = with_memory.invoke(
    {"input": "我的名字是 Alice"},
    config={"configurable": {"session_id": "user123"}}
)
```

## 流式输出

```python
# 流式输出 token
async for chunk in chain.astream({"topic": "AI"}):
    print(chunk.content, end="", flush=True)

# 流式输出事件（用于调试）
async for event in chain.astream_events({"topic": "AI"}, version="v1"):
    print(event)
```

## LangSmith 追踪

```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-api-key"
os.environ["LANGCHAIN_PROJECT"] = "my-project"

# 所有链现在都会自动被追踪
chain.invoke({"topic": "AI"})
```

## LangGraph 工作流（条件路由）

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

# --------------------------------------------------------------------------------
# 构建带条件路由的工作流
# --------------------------------------------------------------------------------
workflow = StateGraph(MessagesState)

# 定义节点
workflow.add_node(generate_query_or_respond)
workflow.add_node("retrieve", ToolNode([retriever_tool]))
workflow.add_node(rewrite_question)
workflow.add_node(generate_answer)

# 设置入口点
workflow.add_edge(START, "generate_query_or_respond")

# 添加条件边：决定是否检索
workflow.add_conditional_edges(
    "generate_query_or_respond",
    tools_condition,
    {"tools": "retrieve", END: END}
)

# 添加检索后的条件边
workflow.add_conditional_edges("retrieve", grade_documents)
workflow.add_edge("generate_answer", END)
workflow.add_edge("rewrite_question", "generate_query_or_respond")

# 编译
graph = workflow.compile()
```

## 相关资源

- **LangChain 文档**: https://python.langchain.com/docs/introduction/
- **LangGraph 文档**: https://langchain-ai.github.io/langgraph/
- **LangSmith**: https://smith.langchain.com/
- **LangChain Hub**: https://smith.langchain.com/hub
- **LangChain 模板**: https://github.com/langchain-ai/langchain/tree/master/templates
