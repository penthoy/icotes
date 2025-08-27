import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv(override=True)

openai_api_key = os.getenv('OPENAI_API_KEY')
google_api_key = os.getenv('GOOGLE_API_KEY')
deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
groq_api_key = os.getenv('GROQ_API_KEY')
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
moonshot_api_key = os.getenv('MOONSHOT_API_KEY')
ollama_url = os.getenv('OLLAMA_URL')
mailersend_api_key = os.environ.get('MAILERSEND_API_KEY')


def get_ali_client():
    """
    Initializes and returns an OpenAI client configured for Aliyun's Dashscope API.
    """
    dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
    if not dashscope_api_key:
        raise ValueError("DASHSCOPE_API_KEY environment variable is not set.")
    
    return OpenAI(
        api_key=dashscope_api_key,
        base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )


def get_openrouter_client():
    """
    Initializes and returns an OpenAI client configured for OpenRouter.
    """
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set.")
    
    return OpenAI(
        api_key=openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": "https://github.com/penthoy/icotes",  # Your app's repository URL
            "X-Title": "icotes",  # Your app's name
        }
    )


def get_openai_client():
    """
    Initializes and returns an OpenAI client configured for OpenAI's API.
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set.")

    return OpenAI(
        api_key=openai_api_key,
        base_url="https://api.openai.com/v1",
    )


def get_google_client():
    """
    Initializes and returns an OpenAI client configured for Google's API.
    """
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set.")

    return OpenAI(
        api_key=google_api_key,
        base_url="https://api.google.com/v1",
    )


def get_deepseek_client():
    """
    Initializes and returns an OpenAI client configured for DeepSeek's API.
    """
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
    if not deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable is not set.")

    return OpenAI(
        api_key=deepseek_api_key,
        base_url="https://api.deepseek.com/v1",
    )


def get_groq_client():
    """
    Initializes and returns an OpenAI client configured for Groq's API.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set.")

    return OpenAI(
        api_key=groq_api_key,
        base_url="https://api.groq.com/v1",
    )


def get_anthropic_client():
    """
    Initializes and returns an OpenAI client configured for Anthropic's OpenAI-compatible API (Claude).
    
    Anthropic provides OpenAI-compatible endpoints at https://api.anthropic.com/v1/chat/completions
    which allows using the OpenAI SDK with Claude models.
    """
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")

    return OpenAI(
        api_key=anthropic_api_key,
        base_url="https://api.anthropic.com/v1",
    )


def get_moonshot_client():
    """
    Initializes and returns an OpenAI client configured for Moonshot's API.
    """
    moonshot_api_key = os.getenv("MOONSHOT_API_KEY")
    if not moonshot_api_key:
        raise ValueError("MOONSHOT_API_KEY environment variable is not set.")

    return OpenAI(
        api_key=moonshot_api_key,
        base_url="https://api.moonshot.ai/v1",
    )


def get_ollama_client():
    """
    Initializes and returns an OpenAI client configured for Ollama's local API.
    
    Uses OLLAMA_URL environment variable
    """
    ollama_url = os.getenv("OLLAMA_URL")
    if not ollama_url:
        raise ValueError("OLLAMA_URL environment variable is not set. Example: http://localhost:11434/v1")
    
    return OpenAI(
        api_key="ollama",  # Ollama uses a fixed API key
        base_url=ollama_url,
    )


