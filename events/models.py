# Create your models here.
# events/models.py
from django.db import models
from django.core.validators import EmailValidator, MinValueValidator
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    venue = models.CharField(max_length=300)
    event_date = models.DateTimeField()
    ticket_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    total_seats = models.PositiveIntegerField()
    available_seats = models.PositiveIntegerField()
    image = models.ImageField(upload_to='event_images/', blank=True, null=True)
    organizer_name = models.CharField(max_length=100)
    organizer_contact = models.CharField(max_length=15)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-event_date']


class Ticket(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    ticket_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name='tickets')

    # User Details
    full_name = models.CharField(max_length=100)
    email = models.EmailField(validators=[EmailValidator()])
    phone = models.CharField(max_length=15)

    # Payment Details
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(
        max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(
        max_length=200, blank=True, null=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS, default='pending')

    # QR Code
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    qr_data = models.CharField(max_length=500, unique=True, blank=True)

    # Attendance
    is_checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_name} - {self.event.title}"

    def generate_qr_code(self):
        """Generate QR code with unique ticket data"""
        qr_string = f"EVENT:{self.event.id}|TICKET:{self.ticket_id}|NAME:{self.full_name}|EMAIL:{self.email}"
        self.qr_data = qr_string

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_string)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        file_name = f'qr_{self.ticket_id}.png'
        self.qr_code.save(file_name, File(buffer), save=False)
        buffer.close()

    def save(self, *args, **kwargs):
        if self.payment_status == 'completed' and not self.qr_code:
            self.generate_qr_code()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['qr_data']),  # Fast QR scanning
            models.Index(fields=['payment_status']),  # Fast queries
        ]
