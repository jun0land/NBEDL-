# reservations/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from .models import Reservation, IssueReport, Equipment, Notice, SystemConfig, UserProfile
import json
from django.views.decorators.http import require_POST


def reservation_page(request):
    # 1. 시스템 제어판 데이터 가져오기 (DB에 없으면 기본값으로 자동 생성)
    config, created = SystemConfig.objects.get_or_create(id=1)

    # 2. [전체 점검 모드] 켜져 있고 관리자가 아니면 점검 페이지로 강제 이동!
    if config.is_maintenance_mode and not request.user.is_staff:
        return render(request, 'reservations/maintenance.html', {'message': config.maintenance_message})

    # --- 기존 예약 신청(POST) 처리 로직 ---
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "로그인이 필요한 서비스입니다.")
            return redirect('login')

        # [미비점 보완] 관리자가 아닌데, 아직 가입 승인이 안 된 유저라면 컷!
        if not request.user.is_staff and hasattr(request.user, 'profile') and not request.user.profile.is_approved:
            messages.error(request, "가입 승인 대기 중입니다. 관리자 승인 후 예약이 가능합니다.")
            return redirect('reservations:reservation_page')    

        # 3. [예약 막아두기 모드] 켜져 있고 관리자가 아니면 예약 차단!
        if config.block_reservations and not request.user.is_staff:
            messages.error(request, "현재 신규 예약이 임시 중단되었습니다.")
            return redirect('reservations:reservation_page')

        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        affiliation = request.POST.get('affiliation')
        sample_name = request.POST.get('sample_name')
        sample_details = request.POST.get('sample_details')
        attached_file = request.FILES.get('attached_file')
        
        equipment_id = request.POST.get('equipment')
        equipment = get_object_or_404(Equipment, id=equipment_id)
        
        overlapping = Reservation.objects.filter(
            equipment=equipment,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()

        if overlapping:
            messages.error(request, "해당 시간에 이 장비는 이미 예약되었거나 점검 중입니다.")
            return redirect('reservations:reservation_page')

        Reservation.objects.create(
            equipment=equipment,
            user=request.user,
            affiliation=affiliation,
            start_time=start_time,
            end_time=end_time,
            sample_name=sample_name,
            sample_details=sample_details,
            attached_file=attached_file
        )
        messages.success(request, f"[{equipment.name}] 예약이 성공적으로 신청되었습니다!")
        return redirect('reservations:reservation_page')

    # --- 기존 달력 화면(GET) 처리 로직 ---
    equipments = Equipment.objects.all()
    
    # ✨ 3번 요청: 상단 고정(is_pinned)된 것을 먼저, 그다음 최신순으로 정렬
    notices = Notice.objects.all().order_by('-is_pinned', '-created_at')[:5] 
    
    # ✨ 4번 요청: 관리자용 승인 대기 중인 신규 가입자 수 계산
    pending_users_count = 0
    if request.user.is_authenticated and request.user.is_staff:
        # 프로필 모델에서 승인 안 된(is_approved=False) 유저 수 카운트
        pending_users_count = UserProfile.objects.filter(is_approved=False).count()
    
    return render(request, 'reservations/calendar.html', {
        'equipments': equipments,
        'notices': notices,
        'block_reservations': config.block_reservations,
        'is_maintenance_mode': config.is_maintenance_mode,
        'pending_users_count': pending_users_count, # ✨ 화면으로 전달
    })

def get_reservations(request):
    events = []
    
    # ✨ 수정 1: 달력 화면에서 장비 필터링을 선택했을 때 필터 작동 로직
    equipment_id = request.GET.get('equipment')
    if equipment_id:
        reservations = Reservation.objects.filter(equipment_id=equipment_id)
    else:
        reservations = Reservation.objects.all()
    
    for res in reservations:
        start_iso = res.start_time.isoformat()
        end_iso = res.end_time.isoformat()
        time_str = f"{res.start_time.strftime('%H:%M')}~{res.end_time.strftime('%H:%M')}"
        
        if res.status == 'APPROVED':
            status_kor = '승인'
        elif res.status == 'REJECTED':
            status_kor = '반려'
        else:
            status_kor = '대기'
            
        equip_name = res.equipment.name if res.equipment else "공통 장비"
        
        if res.is_maintenance:
            events.append({
                'title': f"🛠️ [{equip_name} 점검] {time_str}", 
                'start': start_iso,
                'end': end_iso,    
                'backgroundColor': '#dc3545',
                'borderColor': '#dc3545',
                'textColor': '#ffffff',
                'extendedProps': {
                    'equipment_name': equip_name,
                    'sample_name': '장비 점검', 
                    'sample_details': '관리자가 지정한 점검 시간입니다.'
                }
            })
        else:
            event_color = '#ed542b' if res.status == 'APPROVED' else '#948a88'
            events.append({
                'title': f"[{equip_name}] {time_str} {res.affiliation}", 
                'start': start_iso,
                'end': end_iso,    
                'backgroundColor': event_color,
                'borderColor': event_color,
                'textColor': '#ffffff',
                'extendedProps': {
                    'equipment_name': equip_name,
                    'sample_name': res.sample_name, 
                    'sample_details': res.sample_details
                }
            })
            
    return JsonResponse(events, safe=False)

def mypage(request):
    equipments = Equipment.objects.all()
    selected_equipment = request.GET.get('equipment')
    
    # ✨ 추가: 관리자 알림 배지를 위해 '대기 중(PENDING)'인 예약의 총 개수를 셉니다.
    pending_count = Reservation.objects.filter(status='PENDING').count()
    
    if request.user.is_staff: # 관리자인 경우
        reservations = Reservation.objects.all()
        if selected_equipment:
            reservations = reservations.filter(equipment_id=selected_equipment)
        reservations = reservations.order_by('-start_time')
    else: # 일반 사용자인 경우
        reservations = Reservation.objects.filter(user=request.user).order_by('-start_time')
    
    return render(request, 'reservations/mypage.html', {
        'reservations': reservations,
        'equipments': equipments,
        'selected_equipment': selected_equipment,
        'pending_count': pending_count  # ✨ 개수를 화면(HTML)으로 전달!
    })

def cancel_reservation(request, res_id):
    if not request.user.is_authenticated:
        return redirect('login')
    reservation = get_object_or_404(Reservation, id=res_id)
    
    if reservation.user == request.user or request.user.is_staff:
        reservation.delete()
        messages.success(request, "예약이 성공적으로 취소/삭제되었습니다.")
    else:
        messages.error(request, "본인의 예약만 취소할 수 있습니다.")
    return redirect('reservations:mypage')

def signup(request):
    if request.method == 'POST':
        # 1. HTML 폼에서 입력한 데이터 가져오기
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        affiliation = request.POST.get('affiliation')
        advisor_id = request.POST.get('advisor_id')

        # 2. 필수 값 누락 확인
        if not all([username, password, password_confirm, affiliation, advisor_id]):
            messages.error(request, '모든 항목을 필수적으로 입력해주세요.')
            return render(request, 'reservations/signup.html')

        # 3. 비밀번호 일치 확인
        if password != password_confirm:
            messages.error(request, '비밀번호가 일치하지 않습니다.')
            return render(request, 'reservations/signup.html')

        # 4. 사용자 계정 생성 (중복 아이디 방지)
        try:
            user = User.objects.create_user(username=username, password=password)
            
            # 5. 회원가입 성공 시, UserProfile을 생성하여 소속과 교직원 번호 저장
            UserProfile.objects.create(
                user=user, 
                affiliation=affiliation, 
                advisor_id=advisor_id  # ✨ 추가된 부분
            )
            
            messages.success(request, '회원가입이 완료되었습니다. 관리자의 승인을 기다려주세요.')
            return redirect('reservations:login') # urls 설정에 따라 'login' 또는 'reservations:login'
            
        except IntegrityError:
            messages.error(request, '이미 존재하는 아이디입니다. 다른 아이디를 사용해주세요.')
            return render(request, 'reservations/signup.html')

    # GET 요청 시 빈 폼 화면 렌더링
    return render(request, 'reservations/signup.html')

def report_issue(request):
    if not request.user.is_authenticated:
        messages.error(request, "로그인이 필요한 서비스입니다.")
        return redirect('login')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')

        IssueReport.objects.create(
            user=request.user,
            title=title,
            description=description
        )
        messages.success(request, "오류/고장 신고가 접수되었습니다. 관리자 확인 후 조치하겠습니다.")
        return redirect('reservations:reservation_page')

    return render(request, 'reservations/report_issue.html')

@staff_member_required
def approve_reservation(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    reservation.status = 'APPROVED'
    reservation.rejection_reason = '' 
    reservation.save()
    messages.success(request, f"'{reservation.sample_name}' 예약이 승인되었습니다.")
    return redirect('reservations:mypage')

@staff_member_required
def reject_reservation(request, reservation_id):
    if request.method == 'POST':
        reservation = get_object_or_404(Reservation, id=reservation_id)
        reason = request.POST.get('rejection_reason', '').strip()
        reservation.status = 'REJECTED'
        reservation.rejection_reason = reason
        reservation.save()
        messages.warning(request, f"'{reservation.sample_name}' 예약이 반려되었습니다. (사유: {reason})")
    return redirect('reservations:mypage')

@staff_member_required
def revert_reservation(request, reservation_id):
    if request.method == 'POST':
        reservation = get_object_or_404(Reservation, id=reservation_id)
        reservation.status = 'PENDING'
        reservation.rejection_reason = ''  # 대기로 돌릴 때 기존 반려 사유 초기화
        reservation.save()
        messages.info(request, f"'{reservation.sample_name}' 예약이 다시 '대기' 상태로 복구되었습니다.")
    return redirect('reservations:mypage')

@staff_member_required
def settlement_view(request):
    # 모든 예약 내역 가져오기 (필요하다면 status='COMPLETED' 인 것만 가져오도록 필터링 가능)
    reservations = Reservation.objects.all()
    
    settlement_data = {}

    for res in reservations:
        if not res.equipment or not res.start_time or not res.end_time:
            continue
            
        # 1. 이용 시간 계산
        diff = res.end_time - res.start_time
        hours = diff.total_seconds() / 3600  # 시간 단위로 변환
        
        if hours <= 0:
            continue
            
        # 2. 금액 계산
        cost = round(hours * res.equipment.hourly_rate)
        
        # 3. 소속별로 데이터 누적
        aff = res.affiliation
        if aff not in settlement_data:
            settlement_data[aff] = {
                'total_cost': 0,
                'total_hours': 0,
                'reservation_count': 0
            }
        
        settlement_data[aff]['total_cost'] += cost
        settlement_data[aff]['total_hours'] += hours
        settlement_data[aff]['reservation_count'] += 1

    return render(request, 'reservations/settlement.html', {'settlement_data': settlement_data})

@require_POST
def toggle_system_config(request):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': '권한이 없습니다.'})
        
    data = json.loads(request.body)
    config, _ = SystemConfig.objects.get_or_create(id=1)
    
    if 'is_maintenance_mode' in data:
        config.is_maintenance_mode = data['is_maintenance_mode']
    if 'block_reservations' in data:
        config.block_reservations = data['block_reservations']
        
    config.save()
    return JsonResponse({'success': True})

from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages

# ✨ 디테일한 에러 메시지를 주는 커스텀 로그인 뷰
def custom_login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # 1. 아이디 존재 여부 확인
        if not User.objects.filter(username=username).exists():
            messages.error(request, "등록되지 않은 아이디입니다.")
            return render(request, 'registration/login.html') # 로그인 템플릿 경로에 맞게 수정 필요 시 'reservations/login.html' 사용

        # 2. 비밀번호 확인 및 로그인
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('reservations:reservation_page')
        else:
            messages.error(request, "비밀번호가 틀렸습니다.")
            return render(request, 'registration/login.html')

    return render(request, 'registration/login.html')

import random
import string

def find_password(request):
    temp_password = None
    if request.method == 'POST':
        username = request.POST.get('username')
        advisor_id = request.POST.get('advisor_id')

        try:
            user = User.objects.get(username=username)
            # 유저 프로필이 있고, 교직원 번호가 일치하는지 확인
            if hasattr(user, 'profile') and user.profile.advisor_id == advisor_id:
                # ✨ 일치함! 무작위 8자리 임시 비밀번호 생성
                temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                
                # 장고 내장 함수로 비밀번호 안전하게 변경 및 저장
                user.set_password(temp_password)
                user.save()
            else:
                messages.error(request, "아이디 또는 교직원 번호가 일치하지 않습니다.")
        except User.DoesNotExist:
            messages.error(request, "존재하지 않는 아이디입니다.")

    return render(request, 'reservations/find_password.html', {'temp_password': temp_password})