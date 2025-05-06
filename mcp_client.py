from fastapi import HTTPException
from mcp import ClientSession
from mcp.client.sse import sse_client
from typing import Optional
from contextlib import AsyncExitStack
from google import genai
from config import GOOGLE_API_KEY
from google.genai import types
class McpClient:
    def __init__(self):
        self.tools = []
        self.messages = []
        self.session:Optional[ClientSession]  = None
        self.exit_stack = AsyncExitStack()
        self.client = genai.Client(api_key=GOOGLE_API_KEY)
        
    async def connect_to_server(self,path:str):
        try:
            read,write = await self.exit_stack.enter_async_context(sse_client(url=path))
            self.session = await self.exit_stack.enter_async_context(ClientSession(read,write))
            await self.session.initialize()
            # get all the tools
            # get all the tools
            self.tools = await self.get_mcp_tools()
            print(self.tools)
            return True
                
        except Exception as e:
              raise
        
    async def get_mcp_tools(self):
        try:
            # print(awaitself.session.list_tools())
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
             raise(e)      
    
    async def process_query(self,query:str):
        try:
            """ when user hit the query save in self.messages""" 
            self.messages = [types.Content(role="user",parts=[types.Part(text=query)])]
            # print()
            # print("first message with query",self.messages)
            # print()
            while True:
                """now call the call_llm function to get response from gemini""" 
                response  = await self.call_llm()
                # print("response--->>>",response)
                content = response.candidates[0].content
                parts = content.parts
                
                # print()
                # print("second message with fnction call by llm",self.messages)
                # print()
                
                # if response.candidates[0].content.parts[0].function_call:
                if parts and parts[0].function_call:
                    """After call call_llm llm return the function tool that we send with useer query and all tools fetch from mcp server and now append with self.messages funtion call send by llm according to query"""
                    self.messages.append(
                    types.Content(role=response.candidates[0].content.role,parts=[types.Part(function_call=parts[0].function_call)])
                    )
                    
                    function_call = parts[0].function_call
                    print(f"Function to call: {function_call.name}")
                    print(f"Arguments: {function_call.args}")
                    try:
                        """After get tool send by llm now call that tool to mcp server to fetch data according to that function and append result to self.messages """
                        result = await self.session.call_tool(name=function_call.name,arguments=function_call.args)
                        
                        self.messages.append(
                            types.Content(role="tool_use",
                            parts=[types.Part.from_function_response(
                                name=function_call.name,
                                response={"result":result}
                            )]),
                            
                        )
                        # print()
                        # print("third message from mcp server tool give by llm",self.messages)
                        """now finally send this self.messages list to llm to get final result that get from mcp server by calling tool purpose of this call to llm to get more understandable answer"""
                        # print()
                        final_result = self.client.models.generate_content(
                            model="gemini-2.5-flash-preview-04-17",
                            config=types.GenerateContentConfig(temperature=1),
                            contents=self.messages
                        )
                        self.messages.append(
                            types.Content(role=final_result.candidates[0].content.role,parts=[types.Part(text=final_result.candidates[0].content.parts[0].text)]) 
                        )
                        # print("final_result",final_result.candidates[0].content.parts[0].text)
                        break
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        raise HTTPException(status_code=500, detail=f"Tool call failed: {str(e)}")
                else:
                    print("No function call found in the response.")
                    print(response.candidates[0].content.parts[0].text)
                    self.messages.append(
                            types.Content(
                                role=content.role,
                                parts=[types.Part(text=response.candidates[0].content.parts[0].text)]
                            )
                        
                    )
                    break
            return self.messages
                    
        except Exception as e:
            raise(e)

    async def call_llm(self):
        """Call llm with tools get when app start first time and with self.messages having user quer and user role"""
        try:
            available_tools = [
                types.Tool(
                    function_declarations=[
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": {
                                k: v
                                for k, v in tool.inputSchema.items()
                                if k not in ["additionalProperties", "$schema"]
                            },
                        }
                    ]
                )
                for tool in self.tools
            ]
            # print(available_tools)
            return self.client.models.generate_content(
                    model="gemini-2.5-flash-preview-04-17",
                    config=types.GenerateContentConfig(temperature=1,tools=available_tools),
                    contents=self.messages
                )
        except Exception as e:
            raise(e)

    async def call_tool(self,arguments:dict):
        try:
            # print(a,b,operator)
            response  = await self.session.call_tool(name="mcpCalculator",arguments=arguments)
            return response

        except Exception as e:
             raise(e)
    
    async def clenup(self):
        try:
            await self.exit_stack.aclose()
            print("Disconnected from MCP server")
        except Exception as e:
            raise(e)


# process smjho pura 

# app start fetch tools from mcp server by help of mcp client --> now user send query to fastapi which send request to mcp client (sse) -> now the function process query start which send request to llm with tools and user query(this query with role: user save in self.messages) -->  now llm send response with funtion call according to query(this response save in self.mesages having role:modal parts:having function_call) --> now call the call_tool function which send arguments and tool name send by llm and save response (as role:'user'parts=anser get by mcp server tool give by llm ) --> now send this self.messages which have role:user,parts:query,role:'model',parts:functioncall(get from llm from all tools)and role:'user' parts:result(get from mcp server) to llm to get final result --> then finally send response to user  