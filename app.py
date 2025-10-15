import itertools
import json
from dotenv import load_dotenv
from openai import OpenAI
from PyPDF2 import PdfReader
import gradio as gr
from pydantic import BaseModel
import os

import requests


load_dotenv()

openai=OpenAI()
gemini=OpenAI(api_key=os.getenv("GOOGLE_API_KEY"),base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

reader=PdfReader("safal.pdf")
linkedin = ""
for page in reader.pages:
    text = page.extract_text()
    if text:
        linkedin += text
summary=""
with open("summary.txt", "r",encoding="utf-8") as f:
    summary=f.read()

name = "Safal Mahat"

system_prompt=f"You are acting as {name}.You are answering a questions on {name}'s LinkedIn profile.\
You are given a summary of {name}'s LinkedIn profile.\
If you do not know the answer to any question, use your record_unknown_question tool to record the question that you could not answer,  even if it's about something trivial or unrelated to career.\
If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. " 
system_prompt +=f"The summary and linkedin profile is as follows:\
Summary: {summary} \
Linkedin: {linkedin} \
Please answer the quesion in polite and professional manner.If you don't know the answer, please say you don't know."
system_prompt +=f"With this context,please chat with user always staying in the context of {name}'s LinkedIn profile."



system_prompt_without_tool=f"You are acting as {name}.You are answering a questions on {name}'s LinkedIn profile.\
You are given a summary of {name}'s LinkedIn profile."
system_prompt_without_tool +=f"The summary and linkedin profile is as follows:\
Summary: {summary} \
Linkedin: {linkedin} \
Please answer the quesion in polite and professional manner.If you don't know the answer, please say you don't know."
system_prompt_without_tool +=f"With this context,please chat with user always staying in the context of {name}'s LinkedIn profile."

class Evaluation(BaseModel):
    is_acceptable:bool
    feedback:str

evaluator_system_prompt = f"You are an evaluator that decides whether a response to a question is acceptable. \
You are provided with a conversation between a User and an Agent. Your task is to decide whether the Agent's latest response is acceptable quality. \
The Agent is playing the role of {name} and is representing {name} on their website. \
The Agent has been instructed to be professional and engaging, as if talking to a potential client or future employer who came across the website. \
The Agent has been provided with context on {name} in the form of their summary and LinkedIn details. Here's the information:"

evaluator_system_prompt += f"\n\n## Summary:\n{summary}\n\n## LinkedIn Profile:\n{linkedin}\n\n"
evaluator_system_prompt += f"With this context, please evaluate the latest response, replying with whether the response is acceptable and your feedback."

def evaluator_user_prompt(reply, message, history):
    user_prompt = f"Here's the conversation between the User and the Agent: \n\n{history}\n\n"
    user_prompt += f"Here's the latest message from the User: \n\n{message}\n\n"
    user_prompt += f"Here's the latest response from the Agent: \n\n{reply}\n\n"
    user_prompt += "Please evaluate the response, replying with whether it is acceptable and your feedback."
    return user_prompt




def evaluate(reply, message, history) -> Evaluation:

    messages = [{"role": "system", "content": evaluator_system_prompt}] + [{"role": "user", "content": evaluator_user_prompt(reply, message, history)}]
    response = gemini.beta.chat.completions.parse(model="gemini-2.0-flash", messages=messages, response_format=Evaluation)
    return response.choices[0].message.parsed


def rerun(reply, message, history, feedback):
    updated_system_prompt = system_prompt + "\n\n## Previous answer rejected\nYou just tried to reply, but the quality control rejected your reply\n"
    updated_system_prompt += f"## Your attempted answer:\n{reply}\n\n"
    updated_system_prompt += f"## Reason for rejection:\n{feedback}\n\n"
    
    messages = [{"role": "system", "content": updated_system_prompt}]  + [{"role": "user", "content": message}]


    response = openai.chat.completions.create(model="gpt-4o-mini", messages=messages)
    return response.choices[0].message.content

def chat_with_evaluator(message, history):
  
    if "patent" in message:
        system = system_prompt + "\n\nEverything in your reply needs to be in pig latin - \
              it is mandatory that you respond only and entirely in pig latin"
    else:
        system = system_prompt
   
    print("History:", history)
    messages = [{"role": "system", "content": system}]  + [{"role": "user", "content": message}]
    response = openai.chat.completions.create(model="gpt-4o-mini", messages=messages)
    reply =response.choices[0].message.content
    print(reply)
    evaluation = evaluate(reply, message, history)
    
    if evaluation.is_acceptable:
        print("Passed evaluation - returning reply")
    else:
        print("Failed evaluation - retrying")
        print(evaluation.feedback)
        reply = rerun(reply, message, history, evaluation.feedback)       
    return reply

def chat(message, history):
    system = system_prompt_without_tool  
    messages = [{"role": "system", "content": system}]  + [{"role": "user", "content": message}]
    response = openai.chat.completions.create(model="gpt-4o-mini", messages=messages)
    reply =response.choices[0].message.content
    return reply

def chat_with_tool(message, history):
    print("safal")
    print(system_prompt)
    messages = [{"role": "system", "content": system_prompt}]  + [{"role": "user", "content": message}]
    done=False
    while not done:
        response = openai.chat.completions.create(model="gpt-4o-mini", messages=messages,tools=tools)
        finish_reason=response.choices[0].finish_reason
        # If LLM wants to call a toll, we do that
        if finish_reason=="tool_calls":
            message=response.choices[0].message
            tool_calls=message.tool_calls
            result=handle_tool_calls(tool_calls)
            messages.append(message)
            messages.extend(result)
        else:
            done=True
    return  response.choices[0].message.content        


pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

if pushover_user:
    print(f"Pushover user found and starts with {pushover_user[0]}")
else:
    print("Pushover user not found")

if pushover_token:
    print(f"Pushover token found and starts with {pushover_token[0]}")
else:
    print("Pushover token not found")

def record_user_details(email,name="Name not provided", notes="not provided"):
    push(f"Recording interest from {name} with email {email} and notes {notes}")
    return {"recorded":"ok"}

def record_unknown_question(question):
    push(f"Recording {question} asked that I could not answer")
    return {"recorded":"ok"}

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            }
            ,
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Question that was asked"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools=[{"type":"function","function":record_user_details_json},{"type":"function","function":record_unknown_question_json}]


def handle_tool_calls(tool_calls):
    results=[]
    for tool_call in tool_calls:
        tool_name=tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}", flush=True)

        if tool_name=="record_user_details":
            result=record_user_details(**arguments)
        elif tool_name=="record_unknown_question":
            result=record_unknown_question(**arguments)

        results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool_call.id}) 

    return results    

def push(message):
    print(f"Push: {message}")
    payload = {"user": pushover_user, "token": pushover_token, "message": message}
    requests.post(pushover_url, data=payload)


#if __name__ == "__main__":
   # push("Hello Safal")
    #chat("patent",[{"role": "system", "content": "Hi what is your work experience"}])
interface=gr.ChatInterface(chat_with_tool,title="Safal Mahat's LinkedIn Profile Chatbot")#
interface.launch()