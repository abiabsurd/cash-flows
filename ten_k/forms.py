from django import forms


class ReportForm(forms.Form):
    ticker_symbols = forms.CharField(widget=forms.Textarea)

    def clean(self):
        super().clean()
        self.cleaned_data['ticker_symbols'] = set(
            map(str.upper, map(str.strip, self.cleaned_data.get('ticker_symbols', '').split('\n')))
        )
