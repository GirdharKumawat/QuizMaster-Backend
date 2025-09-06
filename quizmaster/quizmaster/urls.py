 
from django.contrib import admin
from django.urls import path ,include
import accounts

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/user/',include('accounts.urls')),
    path('api/v1/quizzes/',include('quiz.urls')),
    
    
]
