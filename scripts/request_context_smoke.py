import argparse
import asyncio
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.brain.engine import brain_engine
from app.core.redis_client import close_redis
from app.repositories.graph_db import graph_repo


async def run_smoke(message: str, user_id: str, session_id: str, persona: str, sleep_s: float) -> int:
    exit_code = 0
    try:
        response = await brain_engine.process_request(
            user_id=user_id,
            message=message,
            session_id=session_id,
            persona=persona
        )
        print(f"process_request_ok len={len(response)}")
    except Exception as exc:
        exit_code = 1
        print(f"process_request_fail error={exc}")

    try:
        chunks = []
        async for event in brain_engine.process_request_stream(
            user_id=user_id,
            message=message,
            session_id=session_id,
            persona=persona,
            style_profile=None
        ):
            if event.get("type") in ("chunk", "content"):
                chunks.append(event)
        print(f"process_request_stream_ok chunks={len(chunks)}")
    except Exception as exc:
        exit_code = 1
        print(f"process_request_stream_fail error={exc}")

    if sleep_s > 0:
        await asyncio.sleep(sleep_s)

    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="RequestContext live smoke test")
    parser.add_argument("--message", default="Hello", help="Test message")
    parser.add_argument("--user-id", default="smoke-user", help="User id")
    parser.add_argument("--session-id", default="", help="Session id")
    parser.add_argument("--persona", default="friendly", help="Persona name")
    parser.add_argument("--sleep", type=float, default=0.5, help="Sleep seconds for background tasks")
    args = parser.parse_args()

    session_id = args.session_id or f"smoke-{uuid.uuid4().hex[:8]}"

    async def runner() -> int:
        try:
            return await run_smoke(
                message=args.message,
                user_id=args.user_id,
                session_id=session_id,
                persona=args.persona,
                sleep_s=args.sleep
            )
        finally:
            await close_redis()
            await graph_repo.close()

    return asyncio.run(runner())


if __name__ == "__main__":
    raise SystemExit(main())
