from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from config import SERVER_URL
from mcp_client import McpClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from mcp import ClientSession
from mcp.client.sse import sse_client

class QuerySchema(BaseModel):
    query:str

@asynccontextmanager
async def lifespan(app:FastAPI):
    client = McpClient()
    try:
        connected = await client.connect_to_server(f'{SERVER_URL}')
        if not connected:
             raise HTTPException(
                status_code=500, detail="Failed to connect to MCP server"
            )
        app.state.client = client
        print("app start")
        # print(app.state.client)
        yield 
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error during lifespan") from e
    finally:
        # shutdown when app close
        print("app close")
        await client.clenup()

app = FastAPI(title="MCP CLIENT CALCULATOR",lifespan=lifespan)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)



@app.post('/query')
async def caluclator(request:QuerySchema):
    try:
        response  = await app.state.client.process_query(request.query)
        # print (response.status_code)
        print ("response_tool",response)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error {e}") from e
        

if __name__ == "__main__":
    import uvicorn    
    uvicorn.run(app,host='0.0.0.0',port=8000)
