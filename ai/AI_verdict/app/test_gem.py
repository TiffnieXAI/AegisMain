from google import genai

client = genai.Client(api_key="AIzaSyB-wPQDQrvWjglTXDxqkUAEyWj9tuZeu3I")

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="Tell me about yourself in a few words"
)
print(response.text)