# from google import genai
# import time

# key = open("myenv/api_key/api_key.txt", "r").read()

# # 1. Initialize the client (make sure your API key is set)
# client = genai.Client(api_key=key)

# print("Uploading document to Gemini...")
# # 2. Upload your PDF
# # The AI treats every page as an image, so it sees all graphs and charts perfectly.
# uni_doc = client.files.upload(file="Digital_logic.pdf")

# # Optional but recommended: Wait a few seconds to let Google's servers process the file
# time.sleep(5) 

# print("Document uploaded! Asking question...")

# # 3. Create your prompt and ask the question
# # Notice how we pass the uploaded file directly in the 'contents' list
# response = client.models.generate_content(
#     model='gemini-2.5-flash', #~1500 requests per day
#         #gemini-2.5-pro #~50 requests per day
#     contents=[
#         "You are an expert university tutor. Answer my question using ONLY the provided document.",
#         uni_doc,
#         "Δωσε μου ενα παράδειγμα μετατροπής και εξηγησε μου."
#     ]
# )

# print("\n--- TUTOR RESPONSE ---")
# print(response.text)


from flask import Flask, jsonify, request
from openai import OpenAI

app = Flask(__name__)

# Point client to LM Studio local server
client = OpenAI(base_url="http://127.0.0.1:1234", api_key="not-needed")


@app.route("/api/chat", methods=["POST"])
def chat():
  data = request.get_json()
  user_message = data.get("message", "")

  response = client.chat.completions.create(
      model="krikri",  # Or leave generic, LM Studio defaults to the loaded model
      messages=[
          {
              "role": "system",
              "content": (
                  "You are a helpful academic lecture assistant. Answer"
                  " accurately in Greek or English based on the user's prompt."
              ),
          },
          {"role": "user", "content": user_message},
      ],
      temperature=0.3,
  )

  reply = response.choices[0].message.content
  return jsonify({"reply": reply})


if __name__ == "__main__":
  app.run(port=5000, debug=True)