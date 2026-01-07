from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    name: str

    @abstractmethod
    def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        pass
