from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='merchant',
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name='transactions',
                to='ledger.merchant',
            ),
        ),
    ]
