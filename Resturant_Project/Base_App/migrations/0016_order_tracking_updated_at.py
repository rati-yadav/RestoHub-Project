from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Base_App', '0015_service_flow_booking_time_fulfillment'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='tracking_updated_at',
            field=models.DateTimeField(
                auto_now=True,
                help_text='Latest status/assignment update timestamp shown on tracking page.',
            ),
        ),
    ]
