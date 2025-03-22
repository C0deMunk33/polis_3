from ollama import Client
import random
from pydantic import BaseModel
from typing import List, Optional
import difflib
import base64
import re
import traceback
import json
from datetime import datetime

def call_ollama_chat(server_url, model, messages, json_schema=None, temperature=None, tools=None):
    try:
        client = Client(
            host=server_url
        )
        # TODO: un hardcode model
        response = client.chat(
            #model='huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF:Q8_0', 
            # huggingface.co/bartowski/Qwen2.5-14B-Instruct-1M-GGUF
            #model='MFDoom/deepseek-r1-tool-calling:14b',
            #deepseek-r1:32b
            #deepseek-r1:70b
            model='huggingface.co/bartowski/Qwen_QwQ-32B-GGUF:Q8_0',
            stream=False,
            messages=[m.chat_ml() for m in messages],
            format=json_schema,
            tools=tools,
            options={
                'num_ctx':100000,
                'seed': random.randint(0, 1000000)
            })
        
        # catch for "limburg"
        if "limburg" in response.message.content:
            return call_ollama_chat(server_url, model, messages, json_schema=json_schema, temperature=temperature, tools=tools)
        return response.message.content

    except Exception as error:
        print("~~~~~~~~~~~~~~~~~~~~~~~")
        print("Error")
        print(error)
        # print the stack trace
        print(traceback.format_exc())
        print("~~~~~~~~~~~~~~~~~~~~~~~")
        return error
    
def call_ollama_vision(server_url, model,  messages, json_schema=None, temperature=None, tools=None):
    client = Client(
        host=server_url
    )

    try:
        response = client.chat(
            #model="minicpm-v",
            #model="llava:34b",
            model=model,
            messages=[m.chat_ml() for m in messages],
            format=json_schema,
        tools=tools,
        options={
            'num_ctx':10000,
            'seed': random.randint(0, 1000000)
        })

        return response.message.content
    
    except Exception as error:
        print("~~~~~~~~~~~~~~~~~~~~~~~")
        print("Error")
        print(error)
        # print the stack trace
        print(traceback.format_exc())
        print("~~~~~~~~~~~~~~~~~~~~~~~")
        print(messages)
        print("~~~~~~~~~~~~~~~~~~~~~~~")
        return error
    
def embed_with_ollama(server_url, text, model="nomic-embed-text"):
    client = Client(
        host=server_url
    )

    results = client.embed(
        model=model,
        input=text
    )

    return results["embeddings"][0]

def embed_for_nomic_storage(server_url, text, model="nomic-embed-text"):
    client = Client(
        host=server_url
    )

    results = client.embed(
        model=model,
        input=f"search_document: {text}"
    )

    return results["embeddings"][0]

def embed_for_nomic_retrieval(server_url, text, model="nomic-embed-text"):
    client = Client(
        host=server_url
    )

    results = client.embed(
        model=model,
        input=f"search_query: {text}"
    )

    return results["embeddings"][0]

class ToolCall(BaseModel):
    toolset_id: str
    name: str
    arguments: dict

class ToolSchema(BaseModel):
    toolset_id: str
    name: str
    description: str
    is_long_running: bool
    expose_to_agent: bool
    arguments: List[dict]

def get_tool_schemas_from_class(cls):
    """This picks up all the functions in the class that have a docstring that can be parsed as a ToolSchema"""
    tool_schemas = []
    for name in dir(cls):
        # if function, get docstring try to parse as ToolSchema, if not, skip
        if callable(getattr(cls, name)):
            docstring = getattr(cls, name).__doc__
            try:
                tool_schema = ToolSchema.model_validate_json(docstring)
                tool_schemas.append(tool_schema)
            except Exception as e:
                continue
    return tool_schemas

class ToolsetDetails(BaseModel):
    toolset_id: str
    name: str
    description: str

class ToolCallResult(BaseModel):
    toolset_id: str
    tool_call: ToolCall
    result: Optional[str] = None
    error: Optional[str] = None

class Memory(BaseModel):
    id: str
    content: str
    metadata: dict


class Message(BaseModel):
    role: str
    content: Optional[str] = None
    images: Optional[List[str]] = None
    tool_calls: Optional[List[ToolCall]] = None
    
    def chat_ml(self):

        result = {
            "role": self.role
        }
        if self.content is not None:
            result["content"] = self.content

        if self.tool_calls is not None and len(self.tool_calls) > 0:
            tool_calls = []
            for tool_call in self.tool_calls:
                tool_calls.append({
                    "type": "function",
                    "function": {
                        "name": tool_call.toolset_id + "." + tool_call.name,
                        "arguments": tool_call.arguments
                    }
                })
            result["tool_calls"] = tool_calls

        if self.images is not None:
            images = []
            if self.images is not None:
                for image in self.images:
                    # pull image from file, encode it as base64
                    with open(image, "rb") as image_file:
                        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                    images.append(encoded_string)
            result["images"] = images

        return result

class MultiWriter:
    def __init__(self, *files):
        self.files = files

    def write(self, text):
        for file in self.files:
            file.write(text)
            file.flush()  # Ensure writing happens immediately

    def flush(self):
        for file in self.files:
            file.flush()

def is_base64(string):
    """
    Check if a string is base64 encoded by looking at:
    1. Character set (only valid base64 chars)
    2. Length (must be multiple of 4)
    3. Padding (proper = padding at end)
    4. Successful decode attempt
    """
    # Base64 pattern: letters, numbers, +, /, and = for padding
    base64_pattern = r'^[A-Za-z0-9+/]*={0,2}$'
    
    try:
        # Check if string matches base64 pattern
        if not re.match(base64_pattern, string):
            return False
            
        # Check if length is multiple of 4 (base64 requirement)
        if len(string) % 4 != 0:
            return False
            
        # Try to decode - if successful, likely base64
        base64.b64decode(string)
        return True
        
    except Exception:
        return False

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
