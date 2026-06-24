from django.contrib import admin
from .models import Equipment, Reservation, IssueReport, UserProfile, Notice, SystemConfig, EquipmentMaintenance

# ✨ 1. 장비 목록 관리 (약어 표시 및 빠른 수정 추가)
@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'internal_hourly_rate', 'external_hourly_rate']
    list_editable = ['short_name', 'internal_hourly_rate', 'external_hourly_rate'] # ✨ 약어 바로 수정 가능
    search_fields = ['name', 'short_name']

# 📅 2. 예약 관리
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('equipment', 'start_time', 'end_time', 'user', 'sample_name', 'status', 'is_maintenance')
    list_filter = ('equipment', 'status', 'is_maintenance', 'start_time')
    search_fields = ('sample_name', 'user__username', 'equipment__name')

# 🚨 3. 오류 신고 관리
@admin.register(IssueReport)
class IssueReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('title', 'user__username', 'description')

# ⚙️ 4. 시스템 설정 제어판
@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ['id', 'is_maintenance_mode', 'block_reservations', 'maintenance_message']
    list_editable = ['is_maintenance_mode', 'block_reservations', 'maintenance_message']

    def has_add_permission(self, request):
        if SystemConfig.objects.exists():
            return False
        return super().has_add_permission(request)

# 📢 5. 공지사항 관리
@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title', 'content')
    list_filter = ('created_at',)

# 🧑‍🔬 6. 일반 회원 계정 관리 (직접 사용 권한 부여 포함)
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'real_name', 'user_type', 'is_approved', 'affiliation')
    list_filter = ('user_type', 'is_approved')
    search_fields = ('user__username', 'real_name', 'student_id')
    
    filter_horizontal = ('certified_equipment',)

# 🛠️ 7. 장비 점검 일정 관리
@admin.register(EquipmentMaintenance)
class EquipmentMaintenanceAdmin(admin.ModelAdmin):
    list_display = ('equipment', 'start_time', 'end_time', 'reason')
    list_filter = ('equipment', 'start_time')
    search_fields = ('equipment__name', 'reason')

# =================================================================
# ✨ 장고 기본 관리자 페이지(Admin) 메뉴 순서 강제 재배열 로직
# =================================================================
def custom_get_app_list(self, request, app_label=None):
    app_dict = self._build_app_dict(request, app_label)
    if not app_dict:
        return []

    ordering = {
        "Reservation": 1,
        "Notice": 2,
        "IssueReport": 3,
        "Equipment": 4,
        "UserProfile": 5,
        "SystemConfig": 6,
        "EquipmentMaintenance": 7
    }

    app_list = sorted(app_dict.values(), key=lambda x: x['name'].lower())
    
    for app in app_list:
        if app['app_label'] == 'reservations':
            app['models'].sort(key=lambda x: ordering.get(x['object_name'], 999))
            
    return app_list

admin.AdminSite.get_app_list = custom_get_app_list