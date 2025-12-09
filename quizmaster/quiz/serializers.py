# quizzes/serializers.py
from rest_framework import serializers
import uuid
from datetime import datetime

class QuestionSerializer(serializers.Serializer):
    question = serializers.CharField()
    options = serializers.ListField(
        child=serializers.CharField(),
        min_length=4,
        max_length=4
    )
    correct_answer = serializers.CharField()
    explanation = serializers.CharField(allow_blank=True, required=False)

 

class QuizCreateSerializer(serializers.Serializer):
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False)
    topic = serializers.CharField()
    difficulty = serializers.CharField()
    max_participants = serializers.IntegerField()
    pointsPerCorrect = serializers.IntegerField()
    duration = serializers.IntegerField()  # in minutes
    start_time = serializers.DateTimeField()
    questions = QuestionSerializer(many=True)
    created_by = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def create(self, validated_data):
        
        quiz_data = validated_data.copy()   # short unique code
        quiz_data["created_by"] = self.context.get("user") # we will pass user in view
        quiz_data["created_at"] = datetime.utcnow()

        return quiz_data
