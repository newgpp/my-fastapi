from typing import AsyncGenerator
import asyncio
import textwrap

from app.core.concurrency import limited


async def attention_chat() -> AsyncGenerator[str, None]:
    attention = textwrap.dedent("""
        《Attention Is All You Need》中文介绍

        《Attention Is All You Need》是 Google 在 2017
        年提出的一篇里程碑式论文，它首次系统性地提出了 Transformer 架构，并彻底改
        变了自然语言处理（NLP）以及后续人工智能模型的发展方向。该论文的核心观点可
        以概括为一句话：序列建模不再需要循环（RNN）或卷积（CNN），仅靠注意力机制
        就足够了。

        在此之前，主流的序列模型如 RNN、LSTM 和 GRU
        都依赖时间步递归计算，这种结构天然存在并行能力差、长距离依赖难以建模的问
        题。而 Transformer 架构通过自注意力机制（Self-Attention），使得序列中任意
        位置的元素都可以直接与其他位置建立联系，从而高效捕捉全局依赖关系，并且可
        以完全并行计算，极大提升了训练效率。

        论文中提出的 Transformer
        由编码器（Encoder）和解码器（Decoder）组成，每一层都包含多头注意力（Multi-
        Head Attention）和前馈神经网络（Feed Forward Network）。多头注意力的设计允
        许模型从多个子空间同时关注不同的信息模式，而位置编码（Positional Encoding）
        则弥补了模型本身不具备序列顺序感知能力的缺陷。

        Transformer 的提出不仅在机器翻译任务上取得了显著性能提升，还成为后来
        GPT、BERT、T5 等大模型的基础架构。《Attention Is All You Need》因此被普遍
        认为是现代大模型时代的起点，对整个 AI 领域产生了深远而持续的影响。
        """).strip()
    try:
        for t in attention:
            yield t
            await asyncio.sleep(0.03)
    finally:
        print("generator cleaned")


async def llm_stream(sem: asyncio.Semaphore) -> AsyncGenerator[str, None]:
    async with limited(sem):
        async for chunk in attention_chat():
            yield chunk


async def echo_http(sem: asyncio.Semaphore) -> AsyncGenerator[str, None]:
    async with limited(sem):
        async for chunk in attention_chat():
            yield chunk
