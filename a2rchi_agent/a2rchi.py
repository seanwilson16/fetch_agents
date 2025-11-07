from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate
import logging
import re
from typing import List, Dict
from uagents import Context
import os

logging.basicConfig(level=logging.INFO)

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "a2rchi_prompt.txt")

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    prompt_text = f.read()

a2rchi_prompt = PromptTemplate.from_template(prompt_text)

# Helper: load FAISS vector index
def get_vectorstore(index_dir: str = "a2rchi_index") -> FAISS:
    return FAISS.load_local(index_dir, OpenAIEmbeddings(), allow_dangerous_deserialization=True)

def format_history(history: List[Dict[str, str]]) -> str:
    formatted = []
    for turn in history[-10:]:
        role = "User" if turn["role"] == "user" else "A2rchi"
        formatted.append(f"{role}: {turn['content']}")
    return "\n".join(formatted)

# Main question answering function
async def answer_physics_question(user_question: str, ctx: Context, history: List[Dict[str, str]]) -> str:
    """
    Answers a Classical Mechanics (8.01) question using a FAISS-powered context + LLM.
    """
    try:
        vectorstore = get_vectorstore()
        retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})
        docs = await retriever.ainvoke(user_question)
        context = "\n\n".join(doc.page_content.strip() for doc in docs)

        chat_history = format_history(history)

        prompt = a2rchi_prompt.format(
            context=context,
            chat_history=chat_history,
            question=user_question
        )

        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        llm_response = await llm.ainvoke(prompt)

        response = llm_response.content

        # Cleanup formatting artifacts
        response = re.sub(r'\(\s*`', r'`', response)
        response = re.sub(r'`([^`]+)`[)\.,;:!?…]*', r'`\1`', response)

        return response

    except Exception as e:
        logging.error(f"❌ Error answering question: {e}")
        return "Sorry, I couldn’t retrieve an answer. Please try again later."
