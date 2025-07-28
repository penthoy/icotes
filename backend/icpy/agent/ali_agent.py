from clients import get_ali_client

"""
qwen-plus
qwen3-coder-plus
"""

def chat():
    try:
        client = get_ali_client()

        completion = client.chat.completions.create(
            model="qwen3-coder-plus",  # Model list: https://www.alibabacloud.com/help/en/model-studio/getting-started/models
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': 'Who are you?'}
                ]
        )
        print(completion.choices[0].message.content)
    except Exception as e:
        print(f"Error message: {e}")
        print("For more information, see: https://www.alibabacloud.com/help/en/model-studio/developer-reference/error-code")


if __name__ == "__main__":
    chat()