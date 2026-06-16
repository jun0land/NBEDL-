from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    path('login/', views.custom_login_view, name='login'), 
    path('', views.reservation_page, name='reservation_page'),
    path('api/reservations/', views.get_reservations, name='get_reservations'),
    path('mypage/', views.mypage, name='mypage'),
    path('cancel/<int:res_id>/', views.cancel_reservation, name='cancel_reservation'),
    path('signup/', views.signup, name='signup'),
    path('report_issue/', views.report_issue, name='report_issue'),
    
    # 관리자 전용 예약 승인/반려/복구 기능
    path('approve/<int:reservation_id>/', views.approve_reservation, name='approve_reservation'),
    path('reject/<int:reservation_id>/', views.reject_reservation, name='reject_reservation'),
    path('revert/<int:reservation_id>/', views.revert_reservation, name='revert_reservation'),
    path('settlement/', views.settlement_view, name='settlement'),
    # reservations/urls.py 내부
    path('settlement/', views.settlement_view, name='settlement'),
    # ✨ 스위치 API 주소 추가
    path('toggle-config/', views.toggle_system_config, name='toggle_config'),
]