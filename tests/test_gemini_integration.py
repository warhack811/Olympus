import asyncio
import logging
import sys
import os

# Path adjustment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.llm.generator import LLMGenerator, LLMRequest
from app.providers.llm.gemini import gemini_adapter
from app.providers.llm.groq import groq_adapter
from app.core.llm.key_manager import key_manager
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_gemini_fallback")

async def test_gemini_governance():
    settings = get_settings()
    
    # 1. Generator Setup
    gen = LLMGenerator()
    gen.register_provider("gemini", gemini_adapter)
    gen.register_provider("groq", groq_adapter)
    
    # 2. Key Check
    gemini_keys = settings.get_gemini_api_keys()
    logger.info(f"KEYS_FOUND: {len(gemini_keys)}")
    
    # 3. Request
    request = LLMRequest(
        role="orchestrator",
        prompt="Merhaba, sen kimsin? Sadece ismini söyle.",
        temperature=0.1
    )
    
    logger.info("TEST_1_START: Standard")
    try:
        result = await gen.generate(request)
        if result.ok:
            logger.info(f"TEST_1_SUCCESS: Model={result.model}")
            logger.info(f"TEST_1_RESPONSE: {result.text}")
        else:
            logger.error(f"TEST_1_FAILED: {result.text}")
    except Exception as e:
        logger.error(f"TEST_1_EXCEPTION: {e}")

    logger.info("TEST_2_START: Stream")
    try:
        async for chunk in gen.generate_stream(request):
            if chunk.startswith("error:"):
                logger.error(f"TEST_2_STREAM_ERROR: {chunk}")
            else:
                print(chunk, end="", flush=True)
        logger.info("TEST_2_STREAM_DONE")
    except Exception as e:
        logger.error(f"TEST_2_EXCEPTION: {e}")
    print("\n")
    
    # Let things settle
    await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        # Loop'u manuel yönetmek daha güvenli olabilir
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(test_gemini_governance())
        # loop.close() # Kapatmamak SSL hatalarını dindirebilir
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"MAIN_ERROR: {e}")
