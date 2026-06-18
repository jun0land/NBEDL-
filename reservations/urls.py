from django.urls import path
from django.contrib.auth import views as auth_views  # ✨ 이 부분이 누락되어서 발생한 에러입니다!
from . import views

app_name = 'reservations'

urlpatterns = [
    # 로그인 
    path('login/', views.custom_login_view, name='login'),
    
    # 비밀번호 변경 (성공 시 마이페이지로 이동)
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='reservations/password_change.html',
        success_url='/mypage/'
    ), name='password_change'),
    
    # 기본 기능
    path('', views.reservation_page, name='reservation_page'),
    path('api/reservations/', views.get_reservations, name='get_reservations'),
    path('mypage/', views.mypage, name='mypage'),
    path('cancel/<int:res_id>/', views.cancel_reservation, name='cancel_reservation'),
    path('signup/', views.signup, name='signup'),
    path('report_issue/', views.report_issue, name='report_issue'),
    
    # 관리자 전용 및 기타 기능
    path('approve/<int:reservation_id>/', views.approve_reservation, name='approve_reservation'),
    path('reject/<int:reservation_id>/', views.reject_reservation, name='reject_reservation'),
    path('revert/<int:reservation_id>/', views.revert_reservation, name='revert_reservation'),
    path('settlement/', views.settlement_view, name='settlement'),
    path('toggle-config/', views.toggle_system_config, name='toggle_config'),

    path('find_password/', views.find_password, name='find_password'),

    path('export-csv/', views.export_settlement_csv, name='export_csv'),
]