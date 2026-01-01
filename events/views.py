from django.shortcuts import render

# Create your views here.
# events/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
import razorpay
import hmac
import hashlib
from .models import Event, Ticket
from .forms import TicketBookingForm
import json
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache event page for 5 minutes
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id, is_active=True)
    
    if request.method == 'POST':
        # Payment logic (don't cache POST requests)
        pass


razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def event_list(request):
    """Display all active events"""
    events = Event.objects.filter(is_active=True, event_date__gte=timezone.now())
    return render(request, 'events/event_list.html', {'events': events})

def event_detail(request, event_id):
    """Display event details and booking form"""
    event = get_object_or_404(Event, id=event_id, is_active=True)
    
    if request.method == 'POST':
        form = TicketBookingForm(request.POST)
        if form.is_valid():
            if event.available_seats <= 0:
                messages.error(request, 'Sorry, no seats available!')
                return redirect('event_detail', event_id=event_id)
            
            # Create Razorpay order
            amount = int(event.ticket_price * 100)  # Convert to paise
            razorpay_order = razorpay_client.order.create({
                'amount': amount,
                'currency': 'INR',
                'payment_capture': '1'
            })
            
            # Create ticket with pending status
            ticket = Ticket.objects.create(
                event=event,
                full_name=form.cleaned_data['full_name'],
                email=form.cleaned_data['email'],
                phone=form.cleaned_data['phone'],
                amount_paid=event.ticket_price,
                razorpay_order_id=razorpay_order['id'],
                payment_status='pending'
            )
            
            context = {
                'event': event,
                'ticket': ticket,
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'amount': amount,
                'currency': 'INR',
            }
            return render(request, 'events/payment.html', context)
    else:
        form = TicketBookingForm()
    
    return render(request, 'events/event_detail.html', {'event': event, 'form': form})



# In views.py - make atomic transaction more explicit
@csrf_exempt
def payment_success(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_signature = data.get('razorpay_signature')
            
            # Verify signature
            generated_signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode(),
                f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
                hashlib.sha256
            ).hexdigest()
            
            if generated_signature != razorpay_signature:
                return JsonResponse({'status': 'failure', 'message': 'Invalid signature'}, status=400)
            
            # Update ticket - CRITICAL: Lock the rows to prevent race conditions
            with transaction.atomic():
                ticket = Ticket.objects.select_for_update().get(
                    razorpay_order_id=razorpay_order_id
                )
                event = Event.objects.select_for_update().get(id=ticket.event.id)
                
                # Check if already processed (prevent double-processing)
                if ticket.payment_status == 'completed':
                    return JsonResponse({
                        'status': 'success',
                        'ticket_id': str(ticket.ticket_id),
                        'message': 'Payment already processed'
                    })
                
                if event.available_seats <= 0:
                    return JsonResponse({
                        'status': 'failure', 
                        'message': 'No seats available'
                    }, status=400)
                
                ticket.razorpay_payment_id = razorpay_payment_id
                ticket.razorpay_signature = razorpay_signature
                ticket.payment_status = 'completed'
                ticket.save()
                
                event.available_seats -= 1
                event.save()
            
            # Send email (this is OK to be slow, happens after payment confirmed)
            send_ticket_email(ticket)
            
            return JsonResponse({
                'status': 'success',
                'ticket_id': str(ticket.ticket_id),
                'message': 'Payment successful! Check your email for the ticket.'
            })
            
        except Ticket.DoesNotExist:
            return JsonResponse({'status': 'failure', 'message': 'Ticket not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'failure', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'failure', 'message': 'Invalid request'}, status=400)


def send_ticket_email(ticket):
    """Send ticket with QR code via email"""
    subject = f'Your Ticket for {ticket.event.title}'
    message = f"""
    Dear {ticket.full_name},
    
    Thank you for booking a ticket for {ticket.event.title}!
    
    Event Details:
    - Event: {ticket.event.title}
    - Date: {ticket.event.event_date.strftime('%B %d, %Y at %I:%M %p')}
    - Venue: {ticket.event.venue}
    - Ticket ID: {ticket.ticket_id}
    
    Please find your QR code attached. Show this at the entrance for check-in.
    
    Best regards,
    Event Management Team
    """
    
    email = EmailMessage(subject, message, settings.EMAIL_HOST_USER, [ticket.email])
    
    if ticket.qr_code:
        email.attach_file(ticket.qr_code.path)
    
    email.send()

def ticket_confirmation(request, ticket_id):
    """Display ticket confirmation page"""
    ticket = get_object_or_404(Ticket, ticket_id=ticket_id, payment_status='completed')
    return render(request, 'events/ticket_confirmation.html', {'ticket': ticket})

@csrf_exempt
def scan_qr(request):
    """Scan QR code and verify ticket"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            qr_data = data.get('qr_data', '')
            
            # Parse QR data
            ticket = Ticket.objects.get(qr_data=qr_data, payment_status='completed')
            
            if ticket.is_checked_in:
                return JsonResponse({
                    'status': 'warning',
                    'message': 'Ticket already checked in',
                    'ticket': {
                        'name': ticket.full_name,
                        'email': ticket.email,
                        'event': ticket.event.title,
                        'checked_in_at': ticket.checked_in_at.strftime('%Y-%m-%d %I:%M %p')
                    }
                })
            
            # Mark as checked in
            ticket.is_checked_in = True
            ticket.checked_in_at = timezone.now()
            ticket.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'User Found! Check-in successful',
                'ticket': {
                    'name': ticket.full_name,
                    'email': ticket.email,
                    'phone': ticket.phone,
                    'event': ticket.event.title,
                    'ticket_id': str(ticket.ticket_id)
                }
            })
            
        except Ticket.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid ticket or ticket not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error: {str(e)}'
            }, status=500)
    
    return render(request, 'events/scan_qr.html')

def admin_dashboard(request):
    """Admin dashboard for event management"""
    events = Event.objects.all()
    total_tickets = Ticket.objects.filter(payment_status='completed').count()
    checked_in = Ticket.objects.filter(is_checked_in=True).count()
    
    context = {
        'events': events,
        'total_tickets': total_tickets,
        'checked_in': checked_in,
    }
    return render(request, 'events/admin_dashboard.html', context)