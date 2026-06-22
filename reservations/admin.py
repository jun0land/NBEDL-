from django.contrib import admin
from .models import Equipment, Reservation, IssueReport, UserProfile, Notice, SystemConfig, EquipmentMaintenance

# ✨ 1. 장비 목록 관리 (시간당 금액 바로 수정)
@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'hourly_rate']
    list_editable = ['hourly_rate']
    search_fields = ['name']

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

    # 관리자가 실수로 제어판을 여러 개 만드는 것을 방지하는 로직
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
    
    # ✨ 장비들을 좌우 박스로 넘기면서 편하게 다중 선택할 수 있는 위젯 적용
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

    # 💡 원하시는 배치 순서를 숫자로 지정합니다.
    ordering = {
        "Reservation": 1,          # 1. 예약
        "Notice": 2,               # 2. 공지사항
        "IssueReport": 3,          # 3. 오류 접수
        "Equipment": 4,            # 4. 연구장비
        "UserProfile": 5,          # 5. 회원 계정
        "SystemConfig": 6,         # 6. 시스템 제어판
        "EquipmentMaintenance": 7  # 7. 장비 점검
    }

    app_list = sorted(app_dict.values(), key=lambda x: x['name'].lower())
    
    for app in app_list:
        if app['app_label'] == 'reservations':
            # ordering 딕셔너리에 지정된 숫자를 기준으로 정렬 (목록에 없으면 999번으로 맨 밑으로 밀림)
            app['models'].sort(key=lambda x: ordering.get(x['object_name'], 999))
            
    return app_list

# 장고의 기본 AdminSite의 메뉴 리스트 불러오는 함수를 우리가 만든 함수로 덮어쓰기 (Monkey Patching)
admin.AdminSite.get_app_list = custom_get_app_list