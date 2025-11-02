import google.generativeai as genai
import os

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

model = genai.GenerativeModel("gemini-2.5-flash")

def generate_text(prompt):
    try:
        response = model.generate_content(prompt)
        print(response)

        # --- SAFETY FIX: Check for valid text parts ---
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if candidate and hasattr(candidate, "content") and candidate.content.parts:
                text = "".join(part.text for part in candidate.content.parts if hasattr(part, "text"))
                if text.strip():
                    return text.strip()

        # If we reach here, Gemini returned an empty response
        return "Hmm... I didn’t quite catch that 🤔 Could you rephrase your question?"

    except Exception as e:
        return f"⚠️ Gemini text generation failed: {e}"
