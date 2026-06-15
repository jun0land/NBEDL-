# reservations/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.admin.views.decorators import staff_member_required
from .models import Reservation, IssueReport, Equipment

def reservation_page(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "로그인이 필요한 서비스입니다.")
            return redirect('login')

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

    equipments = Equipment.objects.all()
    return render(request, 'reservations/calendar.html', {'equipments': equipments})

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
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('reservations:reservation_page')
    else:
        form = UserCreationForm()
    return render(request, 'reservations/signup.html', {'form': form})

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
    