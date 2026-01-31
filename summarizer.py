"""
Text summarization module using API or simple truncation
"""
from config import (
    SUMMARIZATION_TYPE, OPENAI_API_KEY,
    LLAMA_CPP_MODEL_PATH, LLAMA_CPP_CHAT_FORMAT,
    LLAMA_CPP_N_CTX, LLAMA_CPP_N_THREADS,
    LLAMA_CPP_N_GPU_LAYERS, LLAMA_CPP_TEMPERATURE,
    LLAMA_CPP_MAX_TOKENS
)

_openai_client = None
_llama_cpp_client = None


def _get_openai_client():
    """Lazy initialization of OpenAI client"""
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        if OPENAI_API_KEY:
            _openai_client = OpenAI(api_key=OPENAI_API_KEY)
        else:
            raise ValueError("OPENAI_API_KEY not set")
    return _openai_client


def _get_llama_cpp_client():
    """Lazy initialization of llama_cpp client"""
    global _llama_cpp_client
    if _llama_cpp_client is None:
        try:
            from llama_cpp import Llama
            _llama_cpp_client = Llama(
                model_path=LLAMA_CPP_MODEL_PATH,
                chat_format=LLAMA_CPP_CHAT_FORMAT,
                n_ctx=LLAMA_CPP_N_CTX,
                n_threads=LLAMA_CPP_N_THREADS,
                n_gpu_layers=LLAMA_CPP_N_GPU_LAYERS,
                temperature=LLAMA_CPP_TEMPERATURE,
                max_tokens=LLAMA_CPP_MAX_TOKENS,
                verbose=False
            )
        except ImportError:
            print("llama-cpp-python not installed, LLM summarization will be disabled")
            _llama_cpp_client = False
        except Exception as e:
            print(f"Error loading llama_cpp model: {e}")
            _llama_cpp_client = False
    return _llama_cpp_client


class Summarizer:
    def __init__(self):
        self.summarization_type = SUMMARIZATION_TYPE
    
    def summarize_text(self, text: str, max_length: int = 150, min_length: int = 30) -> str:
        """Summarize text content"""
        if not text or len(text.strip()) < 50:
            return text
        
        text = text[:4000]
        
        try:
            if self.summarization_type == "short":
                return text[:100].strip() + "..."
            elif self.summarization_type == "api":
                return self._summarize_with_api(text)
            elif self.summarization_type == "llama_cpp":
                return self._summarize_with_llama_cpp(text)
            else:
                return text[:200] + "..."
        except Exception as e:
            print(f"Summarization error: {e}")
            return text[:200] + "..."
    
    def _summarize_with_api(self, text: str) -> str:
        """Summarize using OpenAI API"""
        try:
            client = _get_openai_client()
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Кратко изложи суть на русском языке. Максимум 2-3 предложения."},
                    {"role": "user", "content": text}
                ],
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"API summarization error: {e}")
            return text[:200] + "..."
    
    def _summarize_with_llama_cpp(self, text: str) -> str:
        """Summarize using llama_cpp local model"""
        try:
            client = _get_llama_cpp_client()
            if client is False:
                return text[:200] + "..."

            response = client.create_chat_completion(
                messages=[
                    {"role": "system", "content": "Суммируй контекст. Не делай рассуждений, Не давай коментариев, Не делай анализа и не делай выводов. Максимум 1-2 коротких предложения. Ответ дай на русском языке"},
                    {"role": "user", "content": text}
                ]
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"llama_cpp summarization error: {e}")
            return text[:200] + "..."

    def process_image(self, image_path: str) -> str:
        """Process image"""
        try:
            from PIL import Image
            img = Image.open(image_path)
            return f"[Изображение: {img.size[0]}x{img.size[1]} пикселей]"
        except Exception as e:
            return "[Изображение]"
    
    def create_digest(self, messages: list) -> str:
        """Create digest from multiple messages"""
        digest_parts = []
        for i, msg in enumerate(messages, 1):
            summary = msg.get('summary', msg.get('text', '')[:200])
            digest_parts.append(f"{i}. {summary}")
        return "\n".join(digest_parts)


summarizer = Summarizer()