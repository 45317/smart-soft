import logging
import multiprocessing

logger = logging.getLogger("django_rag")

_llm_model = None
_llm_tokenizer = None


def get_llm():
    global _llm_model, _llm_tokenizer
    if _llm_model is not None:
        return _llm_model, _llm_tokenizer

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from .config import get_llm_model_name

    model_name = get_llm_model_name()
    logger.info("Loading LLM: %s", model_name)

    cpu_count = multiprocessing.cpu_count()
    torch.set_num_threads(cpu_count)
    logger.info("Using %d CPU threads", cpu_count)

    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda"
        logger.info("CUDA GPU detected")

    _llm_tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    _llm_model = AutoModelForCausalLM.from_pretrained(
        model_name,
        dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        trust_remote_code=True,
    )

    if device == "cpu":
        _llm_model = _llm_model.to("cpu")

    try:
        torch.compile(_llm_model, mode="reduce-overhead")
        logger.info("Model compiled for faster inference")
    except Exception:
        pass

    logger.info("LLM loaded on %s", device)
    return _llm_model, _llm_tokenizer


def generate_answer(question, context):
    model, tokenizer = get_llm()

    if context and context.strip():
        system_prompt = (
            "You are a helpful assistant. You have access to a knowledge base.\n\n"
            "RULES:\n"
            "1. FIRST, try to answer using the provided context.\n"
            "2. If the context does NOT contain the answer, use your own general knowledge.\n"
            "3. Do NOT say 'not enough information' - always try to answer.\n"
            "4. Provide complete, detailed answers.\n"
            "5. Answer in the same language as the question.\n"
            "6. Never make up facts - if you truly don't know, say so."
        )
        user_message = f"Knowledge base context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    else:
        system_prompt = (
            "You are a helpful assistant. Answer questions using your knowledge. "
            "Provide complete, detailed answers. Answer in the same language as the question."
        )
        user_message = f"Question: {question}\n\nAnswer:"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    import torch

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(text, return_tensors="pt")
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
            do_sample=False,
            repetition_penalty=1.1,
        )

    generated_ids = outputs[0][inputs["input_ids"].shape[1] :]
    answer = tokenizer.decode(generated_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)

    if isinstance(answer, bytes):
        answer = answer.decode("utf-8", errors="replace")

    return str(answer).strip()
