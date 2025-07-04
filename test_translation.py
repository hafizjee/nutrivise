from transformers import pipeline

# Load the Urdu translation model
translator = pipeline("translation", model="Helsinki-NLP/opus-mt-en-ur")

# Test sentence
text = "I have a problem with my bones"

# Translate
translated = translator(text, max_length=512)[0]['translation_text']

# Show output
print("Original:", text)
print("Translated (Urdu):", translated)
