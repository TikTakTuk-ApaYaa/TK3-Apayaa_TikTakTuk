from django.db import models


class DemoVenue(models.Model):
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=80)
    address = models.CharField(max_length=255, blank=True)
    capacity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.name} - {self.city}"


class DemoSeat(models.Model):
    venue = models.ForeignKey(DemoVenue, on_delete=models.CASCADE, related_name='seats')
    section = models.CharField(max_length=60)
    row_number = models.CharField(max_length=20)
    seat_number = models.CharField(max_length=20)
    is_assigned = models.BooleanField(default=False)

    class Meta:
        unique_together = ('venue', 'section', 'row_number', 'seat_number')

    def __str__(self):
        return f"{self.section}-{self.row_number}{self.seat_number}"


class DemoTicketCategory(models.Model):
    name = models.CharField(max_length=80)
    quota = models.PositiveIntegerField(default=0)
    price = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name


class DemoTicket(models.Model):
    STATUS_CHOICES = [
        ('Valid', 'Valid'),
        ('Terpakai', 'Terpakai'),
        ('Dibatalkan', 'Dibatalkan'),
    ]

    ticket_code = models.CharField(max_length=40, unique=True)
    event_name = models.CharField(max_length=120)
    event_datetime = models.CharField(max_length=40)
    venue = models.ForeignKey(DemoVenue, on_delete=models.PROTECT)
    category = models.ForeignKey(DemoTicketCategory, on_delete=models.PROTECT)
    seat = models.ForeignKey(DemoSeat, on_delete=models.SET_NULL, null=True, blank=True)
    order_id = models.CharField(max_length=40)
    customer_name = models.CharField(max_length=120)
    owner_key = models.CharField(max_length=80, default='current_customer')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Valid')

    def __str__(self):
        return self.ticket_code
