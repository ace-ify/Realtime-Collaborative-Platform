import os
import httpx

async def generate_llm_edit(current_text: str, prompt: str) -> str:
    """
    Calls the Groq API (OpenAI-compatible) with the document text and user's instruction.
    Has a fallback mock if no API key is provided.
    """
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("[AI Editor] No GROQ_API_KEY found. Running in MOCK mode.")
        if "professional" in prompt.lower():
            return "Dear colleagues, " + current_text.replace("Alice ", "").replace("Bob ", "") + "Let's align soon."
        return f"{current_text} [AI Edit: Applied prompt '{prompt}']"

    # Groq OpenAI-compatible chat completion URL
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    system_instruction = (
        "You are a collaborative text editor. You will receive a document and a prompt. "
        "Apply the prompt's instruction to the document and return ONLY the final edited document text. "
        "Do not include any explanation, intro, markdown blocks, formatting markers (like quotes), or metadata. "
        "Just the raw updated text. Do not repeat instructions."
    )
    
    # We use Llama-3.3-70b-versatile or llama3-8b-8192 for high speed
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Document content:\n{current_text}\n\nInstruction:\n{prompt}"}
        ],
        "temperature": 0.1
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=15.0)
            if response.status_code == 200:
                result = response.json()
                new_text = result["choices"][0]["message"]["content"].strip()
                return new_text
            else:
                print(f"[AI Editor] Groq API error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[AI Editor] Network exception calling Groq: {str(e)}")
        
    return f"{current_text} [AI Edit: Fallback due to API error]"
