from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

# ✨ 1. 기존 '장비' 테이블에 '시간당 요금'을 하나로 합쳤습니다.
class Equipment(models.Model):
    name = models.CharField(max_length=100) # 예: 스핀 코터, Sputter System
    description = models.TextField(blank=True) # 장비 설명이나 위치
    hourly_rate = models.IntegerField(default=0, verbose_name="시간당 이용 금액(원)") # 추가된 부분!

    def __str__(self):
        return self.name

# 2. 기존 '예약' 테이블
class Reservation(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    affiliation = models.CharField(max_length=100)
    sample_name = models.CharField(max_length=100)
    sample_details = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='PENDING')
    is_maintenance = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True, null=True)
    attached_file = models.FileField(upload_to='reservations/attachments/', blank=True, null=True)

    def __str__(self):
        return f"[{self.affiliation}] {self.sample_name}"

# 3. 오류 신고 테이블
class IssueReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# (기존 코드 생략...)

# ✨ 4. 사용자 추가 정보 (소속 및 승인 여부, 등급 추가)
class UserProfile(models.Model):
    USER_TYPE_CHOICES = (
        ('INTERNAL', '내부 이용자 (동국대)'),
        ('EXTERNAL', '외부 이용자'),
    )
    
    real_name = models.CharField(max_length=50, null=True, blank=True, verbose_name="이름") 
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # ✨ 추가: 내부/외부 이용자 구분
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='EXTERNAL', verbose_name="이용자 구분")
    
    affiliation = models.CharField(max_length=100, verbose_name="소속")
    is_approved = models.BooleanField(default=False, verbose_name="관리자 승인 여부")
    advisor_id = models.CharField(max_length=20, null=True, blank=True, verbose_name="지도교수 교원 번호")

    def __str__(self):
        name = self.real_name if self.real_name else self.user.username
        return f"[{self.get_user_type_display()}] {name} ({self.affiliation})"


# ✨ 5. 공지사항 모델 신규 생성
class Notice(models.Model):
    title = models.CharField(max_length=200, verbose_name="공지 제목")
    content = models.TextField(verbose_name="공지 내용")
    is_pinned = models.BooleanField(default=False, verbose_name='📌 상단 고정')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class SystemConfig(models.Model):
    is_maintenance_mode = models.BooleanField(default=False, verbose_name="전체 사이트 점검 모드 (접속 차단)")
    block_reservations = models.BooleanField(default=False, verbose_name="신규 예약 막아두기 (달력 조회는 가능)")
    maintenance_message = models.CharField(
        max_length=200, 
        default="현재 시스템 정기 점검 중입니다. 이용에 불편을 드려 죄송합니다.", 
        verbose_name="점검 안내 문구"
    )

    class Meta:
        verbose_name = "시스템 제어판"
        verbose_name_plural = "시스템 제어판"

    def __str__(self):
        return "시스템 글로벌 제어판"

# ✨ [업데이트 2번] 개별 장비 점검/고장 관리 모델 추가
class EquipmentMaintenance(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, verbose_name="장비")
    start_time = models.DateTimeField(verbose_name="점검 시작 일시")
    end_time = models.DateTimeField(verbose_name="점검 종료 일시")
    reason = models.CharField(max_length=200, verbose_name="점검 사유", default="정기 점검 및 수리")

    def __str__(self):
        return f"[{self.equipment.name}] 점검 ({self.start_time.strftime('%m/%d')}~{self.end_time.strftime('%m/%d')})"
