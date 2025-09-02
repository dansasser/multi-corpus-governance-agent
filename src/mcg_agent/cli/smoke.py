from __future__ import annotations

import argparse
import asyncio
import json

from mcg_agent.routing.pipeline import GovernedAgentPipeline


async def _amain(prompt: str) -> None:
    pipe = GovernedAgentPipeline()
    out = await pipe.process_request(prompt)
    print(json.dumps({
        "agent_role": out.agent_role,
        "content": out.content,
        "metadata": out.metadata or {},
    }))


def main() -> None:
    parser = argparse.ArgumentParser(description="Quick smoke run through the governed pipeline")
    parser.add_argument("prompt", help="Input prompt")
    args = parser.parse_args()
    asyncio.run(_amain(args.prompt))


if __name__ == "__main__":
    main()

