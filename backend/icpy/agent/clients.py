import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv(override=True)

openai_api_key = os.getenv('OPENAI_API_KEY')
google_api_key = os.getenv('GOOGLE_API_KEY')
deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
groq_api_key = os.getenv('GROQ_API_KEY')
mailersend_api_key = os.environ.get('MAILERSEND_API_KEY')

# if mailersend_api_key:
#     print(f"Mailersend API Key exists and begins {mailersend_api_key[:8]}")
# else:
#     print("Mailersend API Key not set")

# if openai_api_key:
#     print(f"OpenAI API Key exists and begins {openai_api_key[:8]}")
# else:
#     print("OpenAI API Key not set")

# if google_api_key:
#     print(f"Google API Key exists and begins {google_api_key[:2]}")
# else:
#     print("Google API Key not set (and this is optional)")

# if deepseek_api_key:
#     print(f"DeepSeek API Key exists and begins {deepseek_api_key[:3]}")
# else:
#     print("DeepSeek API Key not set (and this is optional)")

# if groq_api_key:
#     print(f"Groq API Key exists and begins {groq_api_key[:4]}")
# else:
#     print("Groq API Key not set (and this is optional)")


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
        base_url="https://api.openrouter.ai/v1",
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
    deepseek_api_key = os.getenv("DEEPOKE_API_KEY")
    if not deepseek_api_key:
        raise ValueError("DEEPOKE_API_KEY environment variable is not set.")

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


