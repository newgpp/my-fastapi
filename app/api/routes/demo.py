from typing import Annotated
import asyncio
import json
import time

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Path, Request, status
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import ChatResponse
from app.db.redis import ping_redis
from app.db.mysql import mysql_ping
from app.db.deps import get_mysql_session


router = APIRouter()


@router.get("/hello")
async def hello(name: str = "World"):
    return {"message": f"Hello {name}"}


# 模拟一个检查权限的函数
async def verify_admin(x_admin_key: Annotated[str, Header()]):
    if x_admin_key != "secret-admin-key":
        raise HTTPException(status_code=403, detail="你不是管理员")
    return x_admin_key


@router.get("/admin-data")
# 只有带了正确 Header 的请求才能进入这个函数
async def get_admin_data(admin_key: Annotated[str, Depends(verify_admin)]):
    """依赖注入。它可以让你把“检查登录状态”、“获取数据库连接”等通用逻辑抽离出来，像插件一样插在任何接口上。"""
    return {"data": "敏感数据"}


@router.get("/student/{student_id}")
async def get_student_info(
    # 1. 路径参数：使用 Path()，可以添加描述和校验（如 ID 必须大于 0）
    student_id: Annotated[int, Path(title="学生ID", gt=0)],
    # 2. Header 参数：使用 Header()
    user_token: Annotated[str | None, Header(description="用户的身份令牌")] = None,
    # 如果 Header 名字比较特殊，可以显式指定
    x_client_version: Annotated[str, Header(alias="X-Client-Version")] = "1.0.0",
):
    """
    获取指定学生的信息，并校验请求头。
    """
    if student_id > 1000:  # 假设 ID 大于 1000 的不存在
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="该学生不存在"
        )

    return {
        "student_id": student_id,
        "token_received": user_token,
        "client_version": x_client_version,
        "status": "success",
    }


@router.post("/chat", response_model=ChatResponse)
async def handle_chat(response: Annotated[ChatResponse, Body()]):
    # 这里会自动根据 type (sql/clarify/block) 进行校验和分发
    return response


async def mock_llm_generator():
    text = (
        "ChatGPT 是由 OpenAI 推出的通用型人工智能助手，核心能力是理解自然语言并生成高质量回复。你可以把它当成一个随时可用的“智能合伙人”，覆盖学习、工作、编程、分析与创作等场景。"
        "它能做什么？\n"
        "1. 问答与解释：从基础概念到进阶原理，快速、结构化讲清楚\n"
        "2. 写作与改稿：文案、邮件、方案、总结、翻译\n"
        "3. 编程助手：写代码、读代码、查错、重构、设计架构\n"
        "4. 分析与推理：做对比、拆问题、给建议、跑思路\n"
        "5. 多模态：理解图片、表格、文本，生成对应内容\n"
        "它是怎么工作的？\n"
        "1. 基于大语言模型（LLM），通过大量文本训练学会语言模式\n"
        "2. 不“查数据库”，而是根据上下文预测最合理的下一步输出\n"
        "3. 会结合你当前对话的上下文持续优化回答\n"
    )
    for char in text:
        yield char
        await asyncio.sleep(0.05)


@router.get("/stream")
async def chat_stream():
    # 使用 StreamingResponse 返回生成器
    return StreamingResponse(mock_llm_generator(), media_type="text/event-stream")


async def long_text_generator():
    # 字符串自动拼接
    text = (
        "ChatGPT 是由 OpenAI 推出的通用型人工智能助手，核心能力是理解自然语言并生成高质量回复。你可以把它当成一个随时可用的“智能合伙人”，覆盖学习、工作、编程、分析与创作等场景。"
        "它能做什么？\n"
        "1. 问答与解释：从基础概念到进阶原理，快速、结构化讲清楚\n"
        "2. 写作与改稿：文案、邮件、方案、总结、翻译\n"
        "3. 编程助手：写代码、读代码、查错、重构、设计架构\n"
        "4. 分析与推理：做对比、拆问题、给建议、跑思路\n"
        "5. 多模态：理解图片、表格、文本，生成对应内容\n"
        "它是怎么工作的？\n"
        "1. 基于大语言模型（LLM），通过大量文本训练学会语言模式\n"
        "2. 不“查数据库”，而是根据上下文预测最合理的下一步输出\n"
        "3. 会结合你当前对话的上下文持续优化回答\n"
    )

    for i in range(0, len(text), 2):
        chunk = text[i : i + 2]
        data = {"time": time.time(), "content": chunk, "is_end": False}
        # SSE协议格式：必须以 "data: "开头，以"\n\n" 结尾
        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        # 模拟模型推理的微小延迟
        await asyncio.sleep(0.05)

    d = {"is_end": True}
    yield f"data: {json.dumps(d)}\n\n"


@router.get("/stream-llm")
async def stream_text():
    return StreamingResponse(
        long_text_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


@router.get("/redis/ping")
async def redis_health(redis: Annotated[Redis, Depends(get_redis)]):
    return {"redis": await ping_redis(redis)}


@router.get("/mysql/ping")
async def mysql_health(session: Annotated[AsyncSession, Depends(get_mysql_session)]):
    return {"mysql": await mysql_ping(session)}
