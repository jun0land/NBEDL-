from django.db import models
from django.contrib.auth.models import User

# ✨ 1. 새롭게 추가된 '장비' 테이블
class Equipment(models.Model):
    name = models.CharField(max_length=100) # 예: 스핀 코터, Sputter System
    description = models.TextField(blank=True) # 장비 설명이나 위치

    def __str__(self):
        return self.name

# 2. 기존 '예약' 테이블 확장
class Reservation(models.Model):
    # ✨ 추가됨: 이 예약이 어떤 장비에 대한 것인지 연결
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

# 3. 오류 신고 테이블 (기존 유지)
class IssueReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title