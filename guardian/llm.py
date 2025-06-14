"""Lightweight LLM interface for Helmhud Guardian."""

from typing import List

import re

import logging
from transformers import AutoTokenizer, AutoModelForCausalLM
from sentence_transformers import SentenceTransformer
import faiss

from .bot import bot
from .utils import strip_bot_mentions

logger = logging.getLogger(__name__)

MODEL_NAME = "mrfakename/Apriel-5B-Instruct-llamafied"
EMB_MODEL_NAME = "all-MiniLM-L6-v2"

_tokenizer = None
_model = None
_emb_model = None
_index = None
_memories: List[str] = []


def invalidate_index() -> None:
    """Mark the in-memory FAISS index as stale."""
    global _index
    _index = None


def _load_models():
    global _tokenizer, _model, _emb_model
    try:
        if _tokenizer is None:
            logger.info("Downloading tokenizer %s", MODEL_NAME)
            _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        if _model is None:
            logger.info("Downloading model %s", MODEL_NAME)
            _model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME, device_map="auto", torch_dtype="auto"
            )
        if _emb_model is None:
            logger.info("Loading embedding model %s", EMB_MODEL_NAME)
            _emb_model = SentenceTransformer(EMB_MODEL_NAME)
    except OSError as e:
        raise RuntimeError(
            f"Failed to download model files for {MODEL_NAME}. "
            "Ensure you have internet access and, if the model is gated, run "
            "`huggingface-cli login` before starting the bot."
        ) from e


def ensure_model_downloaded() -> None:
    """Ensure the tokenizer, model and embedding model are loaded."""
    global _tokenizer, _model, _emb_model

    if _tokenizer is not None and _model is not None and _emb_model is not None:
        return

    try:
        # Check for cached files without loading them in memory
        AutoTokenizer.from_pretrained(MODEL_NAME, local_files_only=True)
        AutoModelForCausalLM.from_pretrained(MODEL_NAME, local_files_only=True)
        SentenceTransformer(EMB_MODEL_NAME)
        logger.info("Model files already present; loading")
    except OSError:
        logger.info("Model files not found locally, downloading...")

    _load_models()


def _build_index():
    global _index, _memories
    remories = []
    for user in bot.user_data.values():
        for r in user.get("remory_strings", []):
            text = r.get("context", "")
            remories.append(strip_bot_mentions(text))
    if not remories:
        _index = None
        _memories = []
        return
    embeddings = _emb_model.encode(remories, convert_to_numpy=True)
    _index = faiss.IndexFlatL2(embeddings.shape[1])
    _index.add(embeddings)
    _memories = remories


def get_similar(text: str, k: int = 5) -> List[str]:
    """Return up to k memory strings most similar to text."""
    _load_models()
    if _index is None:
        _build_index()
    if _index is None or not _memories:
        return []
    emb = _emb_model.encode([text], convert_to_numpy=True)
    scores, idx = _index.search(emb, k)
    results = []
    for i in idx[0]:
        if 0 <= i < len(_memories):
            results.append(_memories[i])
    return results


def generate_reply(prompt: str, max_tokens: int = 300) -> str:
    """Generate a reply from the LLM for a given prompt."""
    _load_models()
    logger.info("Generating reply from LLM")

    inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)
    # Some models (e.g. LLaMA) don't accept token_type_ids. Ensure we never pass
    # them to `generate` even if the tokenizer returned them.
    gen_inputs = {k: v for k, v in inputs.items() if k != "token_type_ids"}
    output = _model.generate(**gen_inputs, max_new_tokens=max_tokens)
    text = _tokenizer.decode(output[0], skip_special_tokens=True)
    text = re.sub(r"<\|end.*?>", "", text)
    # Some models echo the entire prompt. If so, strip everything up to the
    # explicit reply section.
    if "### Reply:" in text:
        text = text.split("### Reply:", 1)[1]
    elif "Reply:" in text:
        text = text.split("Reply:", 1)[1]
    return text.strip()
