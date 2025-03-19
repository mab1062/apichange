from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
import json

app = FastAPI()

# Enable CORS to allow requests from SillyTavern
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins; adjust if you know SillyTavern's origin
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods
    allow_headers=["*"],  # Allows all headers
)

# Get the third-party API URL from an environment variable
THIRD_PARTY_API_URL = os.getenv("THIRD_PARTY_API_URL", "https://default-api.com")

@app.api_route("/hf/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy(request: Request, path: str):
    print(f"Received request: {request.method} {path}")
    # Extract the request body
    body = await request.body()
    headers = dict(request.headers)
    # Remove the 'host' header to prevent forwarding issues
    headers.pop("host", None)
    
    # Process JSON requests to remove frequency_penalty
    if request.headers.get("Content-Type") == "application/json":
        try:
            data = json.loads(body)
            if "frequency_penalty" in data:
                del data["frequency_penalty"]
                print("Removed frequency_penalty from request body")
            body = json.dumps(data).encode("utf-8")
        except json.JSONDecodeError:
            pass  # If the body isn't valid JSON, forward it unchanged
    
    # Construct the target URL and forward the request
    url = f"{THIRD_PARTY_API_URL}/{path}"
    print(f"Forwarding to: {url}")
    response = requests.request(
        method=request.method,
        url=url,
        headers=headers,
        data=body,
        params=request.query_params,
        stream=True,  # Enable streaming for compatibility with streaming responses
    )
    
    # Handle streaming responses (e.g., text/event-stream for OpenAI streaming)
    if response.headers.get("Content-Type") == "text/event-stream":
        return StreamingResponse(response.iter_content(chunk_size=1024), media_type="text/event-stream")
    # Handle non-streaming responses
    else:
        print(response.content)
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )