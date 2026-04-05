from django.contrib import admin
from Base_App.models import *
# Register your models here.

admin.site.register(ItemList)
admin.site.register(Items)
admin.site.register(AboutUs)
admin.site.register(Feedback)
admin.site.register(BookTable)


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'total_amount', 'fulfillment_type', 'payment_method', 'status',
        'tracking_status', 'table_number', 'created_at',
    )
    list_display_links = ('id',)
    list_filter = ('payment_method', 'status', 'tracking_status', 'fulfillment_type')
    search_fields = ('user__username', 'table_number')
    list_editable = ('tracking_status', 'table_number')
    inlines = [OrderLineInline]
