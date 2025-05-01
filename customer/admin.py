from django.contrib import admin
from django.urls import reverse, path
from django.utils.html import format_html
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponseRedirect
from django.contrib.admin.views.decorators import staff_member_required
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'temp_email', 'status_display', 'document_link', 'approve_button')
    list_filter = ('status',)
    actions = ['approve_selected', 'reject_selected']
    readonly_fields = ('verification_token',)

    def status_display(self, obj):
        color = {
            'pending': 'orange',
            'approved': 'blue',
            'rejected': 'red',
            'verified': 'green'
        }.get(obj.status, 'black')
        return format_html('<span style="color: {}">{}</span>', color, obj.get_status_display())
    status_display.short_description = "Status"

    def document_link(self, obj):
        return format_html('<a href="{}" target="_blank">View Document</a>', obj.competency_document.url)
    document_link.short_description = "Document"

    def approve_button(self, obj):
        if obj.status == Customer.PENDING:
            return format_html(
                '<a class="button" href="{}">Approve</a>',
                reverse('admin:customers_customer_approve', args=[obj.pk])
            )
        return ""
    approve_button.short_description = "Actions"

    def approve_selected(self, request, queryset):
        for customer in queryset.filter(status=Customer.PENDING):
            self._approve_customer(request, customer)
    approve_selected.short_description = "Approve selected"

    def reject_selected(self, request, queryset):
        queryset.update(status=Customer.REJECTED)

    def _approve_customer(self, request, customer):
        customer.status = Customer.APPROVED
        customer.save()

        verification_url = request.build_absolute_uri(
            reverse('verify_customer', args=[str(customer.verification_token)]))
        
        # Send email after approval
        send_mail(
            'Complete Your Registration',
            f'Your documents have been approved! Complete registration here: {verification_url}',
            settings.DEFAULT_FROM_EMAIL,
            [customer.temp_email],
            fail_silently=False,
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('approve/<int:customer_id>/',
                self.admin_site.admin_view(self.approve_customer),
                name='customers_customer_approve'),
        ]
        return custom_urls + urls
    
    def approve_customer(self, request, customer_id):
        customer = Customer.objects.get(pk=customer_id)
        self._approve_customer(request, customer)
        return HttpResponseRedirect(reverse('admin:customer_customer_changelist'))
