from django.urls import path
from . import views
from .views import flight_detail, flight_list
urlpatterns = [
    path('', views.index, name='index'),
    path('login', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),
    path('register', views.register_view, name='register'),
    path('flight', flight_list, name = 'flight_list'),
    path('flight/<int:flight_id>/', flight_detail, name='flight_detail'),
    path('verify-email/<str:email>/', views.verify_email, name='verify_email'),
    path('account', views.account, name='account'),
    path('update-account', views.update_account, name='update_account'),
]
