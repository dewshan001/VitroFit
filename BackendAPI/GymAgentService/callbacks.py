"""Custom callbacks for logging and observability."""

import logging
from typing import Any, Dict, List
from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger("gym_agent")
logger.setLevel(logging.INFO)

# Ensure at least one handler is attached so logs are visible
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [gym_agent] %(message)s")
    )
    logger.addHandler(_handler)


class GymAgentLoggingHandler(BaseCallbackHandler):
    """Logs agent actions for debugging and monitoring."""

    def on_llm_start(
        self, serialized: Dict[str, Any], prompts: List[str], **kwargs
    ) -> None:
        model_id = serialized.get("id", ["unknown"])
        if isinstance(model_id, list):
            model_id = model_id[-1]
        logger.info(f"🤖 LLM call started (model: {model_id})")

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, **kwargs
    ) -> None:
        tool_name = serialized.get("name", kwargs.get("name", "unknown"))
        logger.info(f"🔧 Tool '{tool_name}' invoked with: {input_str[:200]}")

    def on_tool_end(self, output: str, **kwargs) -> None:
        preview = str(output)[:200]
        logger.info(f"✅ Tool returned: {preview}...")

    def on_tool_error(self, error: BaseException, **kwargs) -> None:
        logger.error(f"❌ Tool error: {error}")

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        if isinstance(outputs, dict) and "result" in outputs:
            result = outputs["result"]
            if isinstance(result, dict):
                logger.info(
                    f"📊 Enrichment complete — "
                    f"Equipment: {len(result.get('equipment', []))} items, "
                    f"Classes: {len(result.get('classes', []))} items, "
                    f"Confidence: {result.get('confidence', '?')}"
                )

