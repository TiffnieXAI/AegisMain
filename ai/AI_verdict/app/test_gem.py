from google import genai

client = genai.Client(api_key="AIzaSyD3BCB1bZNHN9A_58qeQ9hJHjZPKjLgYm4")

response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="Tell me about yourself in a few words"
)
print(response.text)