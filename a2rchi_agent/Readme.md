# 🤖 A2rchi: Classical Mechanics Physics TA Agent

A2rchi is a conversational AI teaching assistant built to help students taking Classical Mechanics 1 (MIT 8.01). It answers physics questions with context-aware, multi-turn dialogue and follows strict formatting rules for clarity and consistency.

---

## 📚 What It Does

- Answers classical mechanics questions using vector search over course materials (via FAISS).
- Supports **multi-turn conversations** with persistent session history.
- Explains physics in **plain English** with readable math and styling rules.
- Enforces strict MITx formatting for equations.

---

## 🚀 Features

- 🧠 Powered by GPT-4o via LangChain's `ChatOpenAI`
- 🔍 Uses FAISS for fast vector-based context retrieval
- 💬 Multi-turn chat with session history stored in `ctx.storage`
- ✅ Strict response formatting for equations and variable notation

---

## 🧪 Example Prompt

**User:**
What is Newton's second law of motion?

**A2rchi:**

Newton's Second Law of Motion is a fundamental principle in classical mechanics that describes the relationship between the net force acting on an object and the resulting acceleration of that object. The law can be stated as follows:

The acceleration of an object is directly proportional to the net force acting on it and inversely proportional to its mass. The direction of the acceleration is the same as the direction of the net force. (cont'd)

---

## 📖 What Data Is Used for the FAISS Index?

A2rchi uses a FAISS vector index built from official MIT 8.01 course materials to ensure high-quality, grounded responses. The index includes:

- 📘 **Textbook Pages**
  Extracted from the MIT Classical Mechanics textbook, covering core topics like forces, kinematics, energy, rotation, and momentum.

These materials are chunked and embedded using OpenAI’s `text-embedding-3-small` model. The FAISS index retrieves the top 5 semantically relevant chunks for each question, which are then inserted into the prompt alongside the chat history for context-aware responses.
