from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
import csv
import random
import string
from .models import Reservation, Equipment, Notice, SystemConfig, UserProfile, EquipmentMaintenance, IssueReport

# ==========================================
# 1. 예약 달력 화면 및 예약 신청 처리
# ==========================================
def reservation_page(request):
    config, _ = SystemConfig.objects.get_or_create(id=1)

    if config.is_maintenance_mode and not request.user.is_staff:
        return render(request, 'reservations/maintenance.html', {'message': config.maintenance_message})

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "로그인이 필요한 서비스입니다.")
            return redirect('reservations:login')

        if not request.user.is_staff and hasattr(request.user, 'profile') and not request.user.profile.is_approved:
            messages.error(request, "가입 승인 대기 중입니다. 관리자 승인 후 예약이 가능합니다.")
            return redirect('reservations:reservation_page')    

        if config.block_reservations and not request.user.is_staff:
            messages.error(request, "현재 신규 예약이 임시 중단되었습니다.")
            return redirect('reservations:reservation_page')

        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        equipment_id = request.POST.get('equipment')
        equipment = get_object_or_404(Equipment, id=equipment_id)
        
        # 🚨 [업데이트] 해당 장비가 점검 기간과 겹치는지 확인
        maint_overlap = EquipmentMaintenance.objects.filter(
            equipment=equipment,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()

        if maint_overlap:
            messages.error(request, f"선택하신 시간에 [{equipment.name}] 장비는 관리자 점검이 예정되어 있어 예약할 수 없습니다.")
            return redirect('reservations:reservation_page')

        # 기존 예약 겹침 확인
        res_overlap = Reservation.objects.filter(
            equipment=equipment,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exclude(status='REJECTED').exists()

        if res_overlap:
            messages.error(request, "해당 시간에 이 장비는 이미 예약되어 있습니다.")
            return redirect('reservations:reservation_page')

        Reservation.objects.create(
            equipment=equipment,
            user=request.user,
            affiliation=request.POST.get('affiliation'),
            start_time=start_time,
            end_time=end_time,
            sample_name=request.POST.get('sample_name'),
            sample_details=request.POST.get('sample_details'),
            attached_file=request.FILES.get('attached_file')
        )
        messages.success(request, f"[{equipment.name}] 예약 신청이 완료되었습니다!")
        return redirect('reservations:reservation_page')

    equipments = Equipment.objects.all()
    notices = Notice.objects.all().order_by('-is_pinned', '-created_at')[:5] 
    
    pending_users_count = UserProfile.objects.filter(is_approved=False).count() if request.user.is_staff else 0
    
    return render(request, 'reservations/calendar.html', {
        'equipments': equipments,
        'notices': notices,
        'block_reservations': config.block_reservations,
        'is_maintenance_mode': config.is_maintenance_mode,
        'pending_users_count': pending_users_count,
    })

# ==========================================
# 2. 달력 데이터 API (이름 표시 & 점검 일정 표시)
# ==========================================
def get_reservations(request):
    equipment_id = request.GET.get('equipment')
    events = []
    
    reservations = Reservation.objects.exclude(status='REJECTED')
    if equipment_id:
        reservations = reservations.filter(equipment_id=equipment_id)
        
    for res in reservations:
        # ✨ 달력에 이름과 소속 표시
        user_name = res.user.profile.real_name if hasattr(res.user, 'profile') and res.user.profile.real_name else res.user.username
        title_text = f"[{res.equipment.name}] {user_name} ({res.affiliation})"
        
        events.append({
            'id': res.id,
            'title': title_text,
            'start': res.start_time.isoformat(),
            'end': res.end_time.isoformat(),
            'backgroundColor': '#198754' if res.status == 'APPROVED' else '#6c757d',
            'equipment_name': res.equipment.name,
            'sample_name': res.sample_name,
            'sample_details': res.sample_details,
        })
        
    # ✨ 장비 점검 일정 가져와서 달력에 빨간색으로 추가
    maintenances = EquipmentMaintenance.objects.all()
    if equipment_id:
        maintenances = maintenances.filter(equipment_id=equipment_id)
        
    for maint in maintenances:
        events.append({
            'title': f"🛠️ [점검중] {maint.equipment.name}",
            'start': maint.start_time.isoformat(),
            'end': maint.end_time.isoformat(),
            'backgroundColor': '#dc3545',
            'equipment_name': maint.equipment.name,
            'sample_name': '정기 점검 및 수리',
            'sample_details': maint.reason,
        })

    return JsonResponse(events, safe=False)

# ==========================================
# 3. 예약 취소 뷰 (노쇼 방지 로직)
# ==========================================
def cancel_reservation(request, res_id):
    if request.method == 'POST':
        res = get_object_or_404(Reservation, id=res_id)
        
        if request.user.is_staff or res.user == request.user:
            # ✨ 24시간 이내 취소 방지 로직
            if not request.user.is_staff and not res.can_cancel:
                messages.error(request, "사용 시작 24시간 이내에는 직접 취소하실 수 없습니다. 관리자에게 문의해 주세요.")
                return redirect('reservations:mypage')
                
            res.delete()
            messages.success(request, "예약이 취소되었습니다.")
        else:
            messages.error(request, "권한이 없습니다.")
    return redirect('reservations:mypage')

# ==========================================
# 4. 회원가입 뷰 (이름 저장 추가)
# ==========================================
def signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        real_name = request.POST.get('real_name') # ✨ 이름 추가
        affiliation = request.POST.get('affiliation')
        advisor_id = request.POST.get('advisor_id')

        if not all([username, password, password_confirm, real_name, affiliation, advisor_id]):
            messages.error(request, '모든 항목을 필수적으로 입력해주세요.')
            return render(request, 'reservations/signup.html')

        if password != password_confirm:
            messages.error(request, '비밀번호가 일치하지 않습니다.')
            return render(request, 'reservations/signup.html')

        try:
            user = User.objects.create_user(username=username, password=password)
            UserProfile.objects.create(
                user=user, 
                real_name=real_name, 
                affiliation=affiliation, 
                advisor_id=advisor_id
            )
            messages.success(request, '회원가입이 완료되었습니다. 관리자의 승인을 기다려주세요.')
            return redirect('reservations:login')
        except IntegrityError:
            messages.error(request, '이미 존재하는 아이디입니다.')
            return render(request, 'reservations/signup.html')

    return render(request, 'reservations/signup.html')

# ==========================================
# 5. 정산 데이터 CSV 엑셀 다운로드
# ==========================================
def export_settlement_csv(request):
    if not request.user.is_staff:
        messages.error(request, "관리자만 접근 가능합니다.")
        return redirect('reservations:mypage')
        
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig') # 한글 깨짐 방지 BOM
    response['Content-Disposition'] = 'attachment; filename="nbedl_settlement_data.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['예약 상태', '장비명', '예약자 계정', '예약자 실명', '소속', '지도교수 번호', '시작 일시', '종료 일시', '이용 시간(h)', '시간당 요금', '예상 청구금액(원)'])
    
    reservations = Reservation.objects.all().order_by('-start_time')
    
    for res in reservations:
        diff_hours = (res.end_time - res.start_time).total_seconds() / 3600
        cost = round(diff_hours * res.equipment.hourly_rate)
        
        real_name = res.user.profile.real_name if hasattr(res.user, 'profile') and res.user.profile.real_name else "-"
        advisor_id = res.user.profile.advisor_id if hasattr(res.user, 'profile') and res.user.profile.advisor_id else "-"
        
        writer.writerow([
            res.get_status_display(),
            res.equipment.name,
            res.user.username,
            real_name,
            res.affiliation,
            advisor_id,
            res.start_time.strftime('%Y-%m-%d %H:%M'),
            res.end_time.strftime('%Y-%m-%d %H:%M'),
            round(diff_hours, 1),
            res.equipment.hourly_rate,
            cost
        ])
        
    return response

# ==========================================
# (아래는 기존의 나머지 로직들 유지)
# ==========================================
def mypage(request):
    if not request.user.is_authenticated:
        return redirect('reservations:login')

    equipments = Equipment.objects.all()
    selected_equipment = request.GET.get('equipment')

    if request.user.is_staff:
        reservations = Reservation.objects.all().order_by('-start_time')
    else:
        reservations = Reservation.objects.filter(user=request.user).order_by('-start_time')

    if selected_equipment:
        reservations = reservations.filter(equipment_id=selected_equipment)
        
    pending_count = 0
    if request.user.is_staff:
        pending_count = Reservation.objects.filter(status='PENDING').count()

    return render(request, 'reservations/mypage.html', {
        'reservations': reservations,
        'equipments': equipments,
        'selected_equipment': selected_equipment,
        'pending_count': pending_count
    })

from django.contrib.auth import authenticate, login
def custom_login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return redirect('reservations:reservation_page')
        else:
            messages.error(request, '아이디 또는 비밀번호가 올바르지 않습니다.')
    return render(request, 'registration/login.html')

def report_issue(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        if request.user.is_authenticated:
            IssueReport.objects.create(user=request.user, title=title, description=description)
            messages.success(request, "오류가 성공적으로 접수되었습니다. 관리자가 확인 후 조치하겠습니다.")
            return redirect('reservations:reservation_page')
        else:
            messages.error(request, "로그인이 필요합니다.")
            return redirect('reservations:login')
    return render(request, 'reservations/report_issue.html')

def find_password(request):
    temp_password = None
    if request.method == 'POST':
        username = request.POST.get('username')
        advisor_id = request.POST.get('advisor_id')

        try:
            user = User.objects.get(username=username)
            if hasattr(user, 'profile') and user.profile.advisor_id == advisor_id:
                temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                user.set_password(temp_password)
                user.save()
            else:
                messages.error(request, "아이디 또는 교직원 번호가 일치하지 않습니다.")
        except User.DoesNotExist:
            messages.error(request, "존재하지 않는 아이디입니다.")

    return render(request, 'reservations/find_password.html', {'temp_password': temp_password})

def approve_reservation(request, reservation_id):
    if request.user.is_staff and request.method == 'POST':
        reservation = get_object_or_404(Reservation, id=reservation_id)
        reservation.status = 'APPROVED'
        reservation.save()
        messages.success(request, "예약이 승인되었습니다.")
    return redirect('reservations:mypage')

def reject_reservation(request, reservation_id):
    if request.user.is_staff and request.method == 'POST':
        reservation = get_object_or_404(Reservation, id=reservation_id)
        reason = request.POST.get('rejection_reason', '관리자에 의해 반려되었습니다.')
        reservation.status = 'REJECTED'
        reservation.rejection_reason = reason
        reservation.save()
        messages.warning(request, "예약이 반려되었습니다.")
    return redirect('reservations:mypage')

def revert_reservation(request, reservation_id):
    if request.user.is_staff and request.method == 'POST':
        reservation = get_object_or_404(Reservation, id=reservation_id)
        reservation.status = 'PENDING'
        reservation.rejection_reason = None
        reservation.save()
        messages.info(request, "예약이 대기 상태로 복구되었습니다.")
    return redirect('reservations:mypage')

def settlement_view(request):
    if not request.user.is_staff:
        return redirect('reservations:mypage')
    reservations = Reservation.objects.all().order_by('-start_time')
    return render(request, 'reservations/settlement.html', {'reservations': reservations})

import json
def toggle_system_config(request):
    if request.method == 'POST' and request.user.is_staff:
        try:
            data = json.loads(request.body)
            config, _ = SystemConfig.objects.get_or_create(id=1)
            if 'is_maintenance_mode' in data:
                config.is_maintenance_mode = data['is_maintenance_mode']
            if 'block_reservations' in data:
                config.block_reservations = data['block_reservations']
            config.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': '권한이 없습니다.'})