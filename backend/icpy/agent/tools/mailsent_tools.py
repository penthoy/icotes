from agents import Agent, Runner, trace, function_tool
import os
import requests
import asyncio

@function_tool
def send_email(body: str):
    """ Minimal working example of a send mail tool """
    api_key = os.environ.get('MAILERSEND_API_KEY')
    url = "https://api.mailersend.com/v1/email"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "from": {
            "email": "admin@rika.studio",  # Change to your verified sender
            "name": "tazhang"
        },
        "to": [
            {
                "email": "penthoy@gmail.com",  # Change to your recipient
                "name": "tazhang"
            }
        ],
        "subject": "Sales email",
        "text": body
    }
    
    response = requests.post(url, headers=headers, json=data)
    return {"status": "success", "status_code": response.status_code}
