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
cerb_api_key = os.getenv('CEREBRAS_API_KEY')


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
        # Use the OpenAI-compatible endpoint as per Groq docs
        base_url="https://api.groq.com/openai/v1",
    )


def get_cerebras_client():
    """
    Initializes and returns a Cerebras client using the official SDK.

    This client provides an OpenAI-compatible interface:
    client.chat.completions.create(..., stream=True)

    Requires:
    - CEREBRAS_API_KEY environment variable
    - Optional: CEREBRAS_BASE_URL to override the default API URL
    """
    api_key = os.getenv("CEREBRAS_API_KEY")
    if not api_key:
        raise ValueError("CEREBRAS_API_KEY environment variable is not set.")

    try:
        # Import inside function to avoid import errors if SDK isn't installed yet
        from cerebras.cloud.sdk import Cerebras  # type: ignore
    except Exception as e:
        raise ImportError(
            "cerebras-cloud-sdk is not installed. Add 'cerebras_cloud_sdk' to backend/pyproject.toml dependencies and install."
        ) from e

    # Use top-level configured base URL if provided for consistency
    return Cerebras(
        api_key=api_key, 
        # base_url="https://api.cerebras.ai/v1" Only needed for Openai-compatible endpoint
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


