 
from django.contrib import admin

from django.urls import path ,include
import accounts


# return hello to quizmaster on '';
def hello(request):
    from django.http import JsonResponse
    return JsonResponse({"message":"Welcome to QuizMaster API"})
 
urlpatterns = [
    path('', hello),
    path('admin/', admin.site.urls),
    path('api/v1/user/',include('accounts.urls')),
    path('api/v1/quizzes/',include('quiz.urls')),
]
