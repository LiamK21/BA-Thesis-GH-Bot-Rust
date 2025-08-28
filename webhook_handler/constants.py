from webhook_handler.models import LLM

USED_MODELS = [LLM.GPT4o, LLM.LLAMA, LLM.DEEPSEEK]

PROMPT_COMBINATIONS_GEN: dict[str, list[int | str]] = {
    "include_golden_code": [1, 1, 1, 1, 0],
    "include_pr_desc": [0, 1, 0, 0, 0],
    "include_predicted_test_file": [1, 0, 0, 0, 0],
    "sliced": ["LongCorr", "LongCorr", "LongCorr", "No", "No"],
    "include_issue_comments": [0, 1, 1, 1, 0],
}


def get_total_attempts() -> int:
    return len(PROMPT_COMBINATIONS_GEN["include_golden_code"])
