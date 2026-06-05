from django.urls import path
from app.views import *

urlpatterns = [
    path('' , index , name = 'index'),
    path('about/' , about , name='about'),
    path('user_register/' , user_register , name= 'user_register'),
    path('user_login/' , user_login , name='user_login'),
    path('logout/' , logout , name='logout'),
    path('user_dashboard/' , user_dashboard , name='user_dashboard'),
    path('view_profile/' , view_profile , name='view_profile'),
    path('update_profile/' , update_profile, name='update_profile'),
    path('forgot/' , forgot , name='forgot'),
    path('reset_password/' , reset_password ,name='reset_password'),
    path('uploadfile/' , uploadfile , name='uploadfile'),
    path('viewfile/' , viewfile , name='viewfile'),
    path('requestfile/<file_id>/' , requestfile , name='requestfile'),
    path('view_requests/' , view_requests , name='view_requests'),
    path('accept_req/<req_id>/' , accept_req , name='accept_req'),
    path('reject_req/<req_id>/' , reject_req , name='reject_req'),
    path('admin_login/' , admin_login , name='admin_login'),
    path('admin_dashboard/' , admin_dashboard , name='admin_dashboard'),
    path('change_password/' , change_password , name='change_password'),
    path('view_response/' ,view_response , name='view_response'),
    path('authorization/<user_id>/' , authorization , name='authorization'),
    path('view_user/' , view_user , name='view_user'),
    path('download/<file_id>/' , download , name='download') , 
    
]