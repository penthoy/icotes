from clients import get_openrouter_client

"""
qwen-plus
qwen3-coder-plus
"""

def chat():
    try:
        client = get_openrouter_client()

        completion = client.chat.completions.create(
            model="moonshotai/kimi-k2",
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': 'Who are you?'}
                ]
        )
        print(completion.choices[0].message.content)
    except Exception as e:
        print(f"Error message: {e}")

if __name__ == "__main__":
    chat()