from django.urls import path
from . import views

urlpatterns = [
    
    path('signup/',views.signup),
    path('login/',views.login),
    path('isauthenticated/',views.isAuthenticated),
    path('logout/',views.logout),
    path('profile/',views.profile),
    path('refresh-token/',views.cookieTokenRefresh),
    
     
    
   ]