from django.contrib import admin
from .models import Equipment, Reservation, IssueReport, UserProfile, Notice

# ✨ 장비 목록에서 시간당 금액을 바로 수정할 수 있게 세팅
@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'hourly_rate'] # 목록에 이름과 요금 띄우기
    list_editable = ['hourly_rate']        # 요금 칸을 엑셀처럼 바로 수정할 수 있게 만들기!
    search_fields = ['name']

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

from django.contrib import admin
from .models import Equipment, Reservation, IssueReport, UserProfile, Notice

# --- 기존에 있던 등록 코드는 그대로 두세요 ---

# 1. 회원 정보 관리 (소속 및 승인 여부)
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'affiliation', 'is_approved']
    list_editable = ['is_approved'] # 관리자 목록 화면에서 체크박스로 즉시 승인 가능하게 설정!
    search_fields = ['user__username', 'affiliation']


from .models import SystemConfig

@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ['id', 'is_maintenance_mode', 'block_reservations', 'maintenance_message']
    list_editable = ['is_maintenance_mode', 'block_reservations', 'maintenance_message']

    # 관리자가 실수로 제어판을 여러 개 만드는 것을 방지하는 로직
    def has_add_permission(self, request):
        if SystemConfig.objects.exists():
            return False
        return super().has_add_permission(request)

from .models import Notice

# ✨ 관리자 페이지에 공지사항 메뉴 추가
@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at') # 목록에 보일 열
    search_fields = ('title', 'content')                 # 검색창 활성화
    list_filter = ('created_at',)                        # 날짜별 필터 추가

# ✨ 장고 기본 관리자 페이지(Admin) 메뉴 순서 강제 재배열 로직
from django.contrib import admin

def custom_get_app_list(self, request, app_label=None):
    app_dict = self._build_app_dict(request, app_label)
    if not app_dict:
        return []

    # 💡 원하시는 배치 순서를 숫자로 지정합니다.
    ordering = {
        "Reservation": 1,    # 1. 예약
        "Notice": 2,         # 2. 공지사항
        "IssueReport": 3,    # 3. 오류 접수
        "Equipment": 4,      # 4. 연구장비
        "UserProfile": 5,    # 5. 회원 계정
        "SystemConfig": 6    # 6. 시스템 제어판
    }

    app_list = sorted(app_dict.values(), key=lambda x: x['name'].lower())
    
    for app in app_list:
        if app['app_label'] == 'reservations':
            # ordering 딕셔너리에 지정된 숫자를 기준으로 정렬 (목록에 없으면 999번으로 맨 밑으로 밀림)
            app['models'].sort(key=lambda x: ordering.get(x['object_name'], 999))
            
    return app_list

# 장고의 기본 AdminSite의 메뉴 리스트 불러오는 함수를 우리가 만든 함수로 덮어쓰기 (Monkey Patching)
admin.AdminSite.get_app_list = custom_get_app_list