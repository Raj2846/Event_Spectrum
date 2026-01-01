# events/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Event, Ticket

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['title', 'event_date', 'venue', 'ticket_price', 'seats_info', 'is_active', 'created_at']
    list_filter = ['is_active', 'event_date', 'created_at']
    search_fields = ['title', 'venue', 'organizer_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('title', 'description', 'image', 'event_date', 'venue')
        }),
        ('Ticketing', {
            'fields': ('ticket_price', 'total_seats', 'available_seats')
        }),
        ('Organizer Details', {
            'fields': ('organizer_name', 'organizer_contact')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def seats_info(self, obj):
        percentage = (obj.available_seats / obj.total_seats * 100) if obj.total_seats > 0 else 0
        color = 'green' if percentage > 50 else 'orange' if percentage > 20 else 'red'
        return format_html(
            '<span style="color: {};">{}/{}</span>',
            color, obj.available_seats, obj.total_seats
        )
    seats_info.short_description = 'Available/Total'

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'full_name', 'event', 'payment_status', 'is_checked_in', 'created_at']
    list_filter = ['payment_status', 'is_checked_in', 'event', 'created_at']
    search_fields = ['ticket_id', 'full_name', 'email', 'phone', 'razorpay_order_id', 'razorpay_payment_id']
    readonly_fields = ['ticket_id', 'qr_code_display', 'qr_data', 'razorpay_order_id', 'razorpay_payment_id', 
                      'razorpay_signature', 'created_at', 'updated_at', 'checked_in_at']
    
    fieldsets = (
        ('Ticket Information', {
            'fields': ('ticket_id', 'event', 'payment_status', 'amount_paid')
        }),
        ('User Details', {
            'fields': ('full_name', 'email', 'phone')
        }),
        ('Payment Details', {
            'fields': ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature')
        }),
        ('QR Code', {
            'fields': ('qr_code_display', 'qr_data')
        }),
        ('Check-in Status', {
            'fields': ('is_checked_in', 'checked_in_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def qr_code_display(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="200" height="200" />', obj.qr_code.url)
        return "No QR Code"
    qr_code_display.short_description = 'QR Code'
    
    actions = ['mark_as_checked_in', 'export_tickets']
    
    def mark_as_checked_in(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(is_checked_in=False).update(
            is_checked_in=True, 
            checked_in_at=timezone.now()
        )
        self.message_user(request, f'{updated} ticket(s) marked as checked in.')
    mark_as_checked_in.short_description = 'Mark selected tickets as checked in'
    
    def export_tickets(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="tickets_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Ticket ID', 'Name', 'Email', 'Phone', 'Event', 'Payment Status', 
                        'Amount', 'Checked In', 'Created At'])
        
        for ticket in queryset:
            writer.writerow([
                str(ticket.ticket_id),
                ticket.full_name,
                ticket.email,
                ticket.phone,
                ticket.event.title,
                ticket.payment_status,
                ticket.amount_paid,
                'Yes' if ticket.is_checked_in else 'No',
                ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    export_tickets.short_description = 'Export selected tickets to CSV'