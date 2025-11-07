# Anime.js Helper Agent 🎨💫

An intelligent AI-powered coding assistant that helps you create beautiful, interactive animations using the [anime.js](https://animejs.com/) library — directly from natural language prompts.

Simply describe your animation idea, and the agent will:

1. Retrieve relevant examples and syntax from an indexed Anime.js documentation knowledge base (via FAISS).
2. Generate HTML, CSS, and JavaScript code using **ES module syntax**.
3. Provide a **LiveCodes** link so you can view and edit the full project instantly — including the JS, HTML, and CSS in one place.

Check the official [anime.js documentation](https://animejs.com/documentation) to see all of the library's capabilities!

---

## ✨ Features

- **Natural language to code**: Just say what you want, the agent writes the code for you.
- **RAG-powered context**: Uses FAISS vector search over the Anime.js documentation to ensure accurate syntax and examples.
- **Live preview**: Click the LiveCodes link to instantly run and edit your animation online.
- **Multi-file support**: Generated HTML, CSS, and JavaScript are all included in the LiveCodes project.
- **Safe ES module imports**: Imports the exact functions needed from Anime.js (`createTimeline`, `createDraggable`, etc.).

---

## 🗂 Project Structure

```text
animejs_agent/
├─ agent.py                 # Starts the agent (uAgents server/mailbox/registration)
├─ chat_proto.py            # Chat protocol handlers; formats the final message
├─ animejs.py               # Code-generation + LiveCodes link builder + RAG wiring
├─ animejs_docs_faiss_index/  # Saved FAISS index (folder with index.faiss + index.pkl)
└─ README.md
```

---

## 💡 Example Usage

**Prompt:**
Make me a red square that rotates when clicked.

**Response:**
✨ Here’s the JavaScript using the **anime.js** library to bring your request to life:

```javascript
import { animate } from "animejs";

const square = document.querySelector(".square");

square.addEventListener("click", () => {
  animate(square, {
    rotate: "1turn",
    duration: 1000,
    easing: "easeInOutQuad",
  });
});
```

🚀 [**Click here to run it instantly on LiveCodes**](https://livecodes.io/?active=script&template=javascript&html=%3C%21DOCTYPE%20html%3E%0A%3Chtml%20lang%3D%22en%22%3E%0A%3Chead%3E%0A%20%20%3Cmeta%20charset%3D%22UTF-8%22%3E%0A%20%20%3Cmeta%20name%3D%22viewport%22%20content%3D%22width%3Ddevice-width%2C%20initial-scale%3D1.0%22%3E%0A%20%20%3Ctitle%3EAnime.js%20Demo%3C/title%3E%0A%20%20%3Clink%20rel%3D%22stylesheet%22%20href%3D%22styles.css%22%3E%0A%3C/head%3E%0A%3Cbody%3E%0A%20%20%3Cdiv%20class%3D%22square%22%3E%3C/div%3E%0A%20%20%3Cscript%20type%3D%22module%22%20src%3D%22script.js%22%3E%3C/script%3E%0A%3C/body%3E%0A%3C/html%3E&css=.square%20%7B%0A%20%20width%3A%20100px%3B%0A%20%20height%3A%20100px%3B%0A%20%20background-color%3A%20red%3B%0A%20%20margin%3A%20100px%20auto%3B%0A%20%20cursor%3A%20pointer%3B%0A%7D&js=import%20%7B%20animate%20%7D%20from%20%27animejs%27%3B%0A%0Aconst%20square%20%3D%20document.querySelector%28%27.square%27%29%3B%0A%0Asquare.addEventListener%28%27click%27%2C%20%28%29%20%3D%3E%20%7B%0A%20%20animate%28square%2C%20%7B%0A%20%20%20%20rotate%3A%20%271turn%27%2C%0A%20%20%20%20duration%3A%201000%2C%0A%20%20%20%20easing%3A%20%27easeInOutQuad%27%0A%20%20%7D%29%3B%0A%7D%29%3B)

🎨 When you open it, you can also explore and edit the corresponding **HTML** and **CSS** for full customization!

---

## 🔗 LiveCodes Integration

Links are generated like:

```ruby
https://livecodes.io/?active=script&template=javascript&html=...&css=...&js=...
```

- `?active=script` opens the **JavaScript** editor by default.
- Users can also view and edit the **HTML** and **CSS** panes within LiveCodes.

---

## 🙌 Credits

- **[Anime.js](https://animejs.com/)** was created by **Julian Garnier**.
- All animation functionality is powered by this excellent open-source library.
- Agent built by _Sean Wilson_.
