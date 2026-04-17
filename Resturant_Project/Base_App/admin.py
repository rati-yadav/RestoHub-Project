from django.contrib import admin

from .models import (
    AboutUs,
    BookTable,
    Cart,
    Feedback,
    ItemList,
    Items,
    Order,
    OrderLine,
)

admin.site.register(ItemList)
admin.site.register(Items)
admin.site.register(AboutUs)
admin.site.register(Feedback)
admin.site.register(BookTable)
admin.site.register(Cart)


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'total_amount',
        'fulfillment_type',
        'payment_method',
        'status',
        'tracking_status',
        'tracking_updated_at',
        'table_number',
        'created_at',
    )
    list_display_links = ('id',)
    list_filter = ('payment_method', 'status', 'tracking_status', 'fulfillment_type')
    search_fields = ('user__username', 'table_number')
    list_editable = ('tracking_status', 'table_number')
    readonly_fields = ('tracking_updated_at',)
    inlines = [OrderLineInline]
