from django.contrib import admin
from .models import Reservation, IssueReport, Equipment

# 🔬 1. 장비 관리자 창 등록
@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')
    search_fields = ('name',)

# 📅 2. 예약 관리자 창 등록
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    # 리스트에 어떤 장비(equipment)의 예약인지도 함께 보여줍니다.
    list_display = ('equipment', 'start_time', 'end_time', 'user', 'sample_name', 'status', 'is_maintenance')
    # 장비별, 상태별로 필터링할 수 있게 기능을 확장했습니다.
    list_filter = ('equipment', 'status', 'is_maintenance', 'start_time')
    search_fields = ('sample_name', 'user__username', 'equipment__name')

# 🚨 3. 오류 신고 관리자 창 등록
@admin.register(IssueReport)
class IssueReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'user__username', 'description')