from openai import AsyncOpenAI

from app.config import Settings


class MissingApiKeyError(RuntimeError):
    pass


def build_sync_prompt(direction: str, source_text: str, target_text: str) -> list[dict[str, str]]:
    if direction == "en_to_zh":
        user_content = (
            "英文修改后段落：\n"
            f"{source_text}\n\n"
            "当前中文对应段落：\n"
            f"{target_text}\n\n"
            "请生成忠实反映英文修改的中文论文段落。"
        )
    elif direction == "zh_to_en":
        user_content = (
            "中文修改后段落：\n"
            f"{source_text}\n\n"
            "当前英文对应段落：\n"
            f"{target_text}\n\n"
            "Please generate an English manuscript paragraph that faithfully reflects the Chinese revision."
        )
    else:
        raise ValueError(f"Unsupported direction: {direction}")

    return [
        {
            "role": "system",
            "content": (
                "你是论文双语同步助手。保持学术论文语气，忠实反映修改，"
                "不要添加原文没有的新信息，不要解释，不要使用 Markdown，只返回建议段落文本。"
            ),
        },
        {"role": "user", "content": user_content},
    ]


class AIClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def suggest(self, direction: str, source_text: str, target_text: str) -> str:
        if not self.settings.has_openai_key:
            raise MissingApiKeyError("OPENAI_API_KEY is not configured")
        if not self.settings.openai_model.strip():
            raise MissingApiKeyError("OPENAI_MODEL is not configured")

        client = AsyncOpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url,
        )
        response = await client.chat.completions.create(
            model=self.settings.openai_model,
            messages=build_sync_prompt(direction, source_text, target_text),
            temperature=0.2,
        )
        suggestion = response.choices[0].message.content or ""
        return suggestion.strip()
