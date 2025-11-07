from typing import Dict
from openai import OpenAI
import os
from uagents import Context
import json
from urllib.parse import quote

# RAG: LangChain imports
from langchain_community.vectorstores import FAISS
from langchain_openai.embeddings import OpenAIEmbeddings


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Load your FAISS index
embedding = OpenAIEmbeddings()
vectorstore = FAISS.load_local("animejs_docs_faiss_index", embedding, allow_dangerous_deserialization=True)
retriever = vectorstore.as_retriever(search_kwargs={"k": 8})

# Prompt template using {context} and {description}
PROMPT_TEMPLATE = """**IMPORTANT: DO NOT format the output using Markdown, triple backticks, or code fencing. Just output a raw JSON object as plain text.**

You are a helpful assistant that generates front-end animation demos using the anime.js library.

You may refer to the anime.js module documentation provided below:
-----
{context}
-----

When given a user’s animation description, return a JSON object with three string fields:

- "html" — the full HTML content, including a `<script type="module">` tag that imports anime.js using, for example:
  `import {{ createDraggable, ... }} from 'animejs';`

- "css" — the complete CSS styles.

- "js" — the complete JavaScript file using **ES module syntax**, importing only the functions you need from `'animejs'`.

Requirements:
- Use the anime.js **ES module build** only. Do not use global `anime` or `<script src="...">` tags.
- Rely on anime.js helpers like `createDraggable`, `createTimeline`, etc., instead of manual DOM wiring.
- Write clean, minimal, and fully self-contained files. Avoid global variables and inline event handlers.
- Output MUST be a single valid JSON object. No extra explanation or formatting.
- Inside each field, preserve proper indentation and line breaks exactly as you would in a normal file.

Now, return a raw JSON object with the requested files for this user request:
"{description}"
"""


async def generate_code(ctx: Context, description: str) -> Dict[str, str]:
    ctx.logger.info("Calling FAISS retriever for RAG context")

    try:
        # 1. Query FAISS index
        docs = retriever.get_relevant_documents(description)
        context = "\n\n---\n\n".join(d.page_content for d in docs)
        ctx.logger.info(f"Retrieved context: {context}")

        # 2. Format prompt
        prompt = PROMPT_TEMPLATE.format(context=context, description=description)

        ctx.logger.info("Calling OpenAI with retrieved context")

        # 3. Call GPT-4o
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        raw = response.choices[0].message.content
        ctx.logger.info(f"Parsing OpenAI response: {raw}")

        code_blocks = json.loads(raw)
        return {
            "html": code_blocks.get("html", "").strip(),
            "css": code_blocks.get("css", "").strip(),
            "js": code_blocks.get("js", "").strip()
        }

    except Exception as e:
        ctx.logger.error(f"OpenAI or RAG error: {e}")
        raise


async def generate_livecodes_link(html: str, css: str, js: str) -> str:
    return (
        "https://livecodes.io/"
        + "?active=script"
        + "&template=javascript"
        + f"&html={quote(html)}"
        + f"&css={quote(css)}"
        + f"&js={quote(js)}"
    )
