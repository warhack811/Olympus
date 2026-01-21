import asyncio
from app.services.brain.task_runner import task_runner
from app.services.brain.intent import TaskSpec
from app.core.terminal import log

async def verify_tool_logging():
    log.section("TOOL LOGGING TEST")
    
    # 1. Test Search Logging
    log.step("🔍", "Testing Search Tool Output")
    search_task = TaskSpec(
        id="t1",
        type="tool",
        tool_name="search_tool",
        params={"query": "dolar ne kadar"}
    )
    await task_runner._execute_tool(search_task)
    
    print("-" * 30)

    # 2. Test Image Gen Logging
    log.step("🎨", "Testing Image Tool Output")
    image_task = TaskSpec(
        id="t2",
        type="tool",
        tool_name="flux_tool",
        params={"prompt": "cyberpunk city", "user_id": "test_user"}
    )
    # Note: This might fail if Redis is down, but we just want to see the LOG before execution
    try:
        await task_runner._execute_tool(image_task)
    except Exception as e:
        log.warning(f"Image gen failed (expected if local): {e}")

if __name__ == "__main__":
    asyncio.run(verify_tool_logging())
