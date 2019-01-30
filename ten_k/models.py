from django.db import models


class Report(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)


class CashFlowsStatement(models.Model):
    report = models.ForeignKey('Report', models.CASCADE, related_name='statements')
    ticker_symbol = models.CharField(max_length=5)
    data = models.TextField()


# class FiscalPeriodData(models.Model):
#     label = models.CharField(max_length=32)
#     statement = models.ForeignKey('CashFlowsStatement', related_name='fiscal_periods')
#
#
# class Row(models.Model):
#     label = models.CharField(max_length=128)
#
#
#
