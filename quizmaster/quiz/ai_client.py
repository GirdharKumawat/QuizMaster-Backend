import json

from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load variables from .env file first.
load_dotenv()


class QuizAIClient:
	def __init__(self):
		# The client automatically picks up GEMINI_API_KEY from the environment.
		self.client = genai.Client()
		self.model_name = "gemini-2.5-flash"  # Highly recommended for JSON speed.

	def generate_questions(
		self,
		topic: str,
		focus: str = "general concepts",
		difficulty: str = "medium",
		count: int = 5,
	) -> list:
		json_schema = """
		[
			{
				"question": "The question text",
				"options": ["Option A", "Option B", "Option C", "Option D"],
				"correct_answer": "The exact string of the correct option",
				"explanation": "A brief explanation of the correct answer"
			}
		]
		"""

		prompt = f"""
		You are an expert quiz creator. Generate {count} multiple-choice questions about "{topic}" & mainly focus on {focus}.
		The difficulty level should be {difficulty}.

		Rules:
		1. There must be exactly 4 options per question.
		2. The correct_answer must perfectly match one of the strings in the options array.
		3. Make the questions engaging and accurate.

		You MUST return the output STRICTLY as a JSON array matching this schema:
		{json_schema}
		"""

		try:
			# Use standard generate_content (NOT stream) to ensure the full JSON block.
			response = self.client.models.generate_content(
				model=self.model_name,
				contents=prompt,
				config=types.GenerateContentConfig(
					response_mime_type="application/json",
					temperature=0.7,
				),
			)

			return json.loads(response.text)
		except Exception as exc:
			print(f"AI Generation Failed: {exc}")
			return []
