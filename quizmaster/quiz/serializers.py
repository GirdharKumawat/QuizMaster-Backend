from rest_framework import serializers

# --------------------------------------
# 1. QUESTION SERIALIZER
# --------------------------------------
class QuestionSerializer(serializers.Serializer):
    question = serializers.CharField()
    options = serializers.ListField(
        child=serializers.CharField(),
        min_length=4, 
        max_length=4
    )
    correct_answer = serializers.CharField()

class PlayerQuestionSerializer(serializers.Serializer):
    """For students: No correct_answer field"""
    question = serializers.CharField()
    options = serializers.ListField(child=serializers.CharField())

# --------------------------------------
# 2. PARTICIPANT SERIALIZER (NEW)
# --------------------------------------
class ParticipantSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    name = serializers.CharField()
    score = serializers.IntegerField()
    status = serializers.CharField()
    quiz_start_time = serializers.DateTimeField(allow_null=True)
    

# --------------------------------------
# 3. QUIZ SESSION RESPONSE SERIALIZER
# --------------------------------------
class QuizSessionSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    quiz_id = serializers.CharField()
    title = serializers.CharField()
    topic = serializers.CharField()
    description = serializers.CharField()
    difficulty = serializers.CharField()
    duration = serializers.IntegerField()
    pointsPerCorrect = serializers.IntegerField()
    status = serializers.CharField()
    host_id = serializers.CharField()
    created_at = serializers.DateTimeField()
    
    max_participants = serializers.IntegerField()
    participant_count = serializers.IntegerField()
    question_count = serializers.IntegerField()
    
    # NEW: Now a list of objects, not strings
    participants = ParticipantSerializer(many=True)

# --------------------------------------
# 4. INPUT SERIALIZERS
# --------------------------------------
class QuizCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField()
    topic = serializers.CharField()
    difficulty = serializers.ChoiceField(choices=["easy", "medium", "hard"])
    duration = serializers.IntegerField(min_value=1)
    max_participants = serializers.IntegerField(min_value=1)
    pointsPerCorrect = serializers.IntegerField(min_value=1)
    questions = QuestionSerializer(many=True, allow_empty=False)

class JoinQuizSerializer(serializers.Serializer):
    session_id = serializers.CharField()

class SubmitAnswerSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    question_index = serializers.IntegerField()
    selected_option = serializers.CharField()