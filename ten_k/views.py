from django.forms import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET
from lxml import etree, html
import requests

from .forms import ReportForm
from .models import CashFlowsStatement, Report


def create_report(request):
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            cash_flows = {}
            for ts in form.cleaned_data['ticker_symbols']:
                try:
                    try:
                        cash_flows[ts] = get_cash_flows_data(ts)
                    except ValueError as e:
                        raise ValidationError('Failed retrieving data') from e
                except ValidationError as e:
                    form.add_error('ticker_symbols', e)

            report = Report.objects.create()
            for ticker, data in cash_flows.items():
                CashFlowsStatement.objects.create(report=report, ticker_symbol=ticker, data=data)

            return redirect('report', pk=report.pk)
    else:
        form = ReportForm()

    return render(request, 'create_report.html', {'form': form})


def get_cash_flows_data(ticker):
    ten_k_filing_node = get_ten_k_filing_node(ticker)
    filing_url = get_filing_url(ten_k_filing_node)
    xbrl_url = get_xbrl_url(ten_k_filing_node)
    cash_flows_report_id = get_cash_flows_report_id(xbrl_url)
    cash_flows_url = get_cash_flows_report_url(filing_url, cash_flows_report_id)
    table_node = get_cash_flows_table(cash_flows_url)

    return cash_flows_html_to_string(table_node)


def get_ten_k_filing_node(ticker):
    params = {'CIK': ticker, 'type': '10-k', 'output': 'xml'}
    resp = requests.get('https://www.sec.gov/cgi-bin/browse-edgar', params)
    try:
        tree = html.fromstring(resp.content)
        return tree.xpath('//filing[1]')[0]

    except (etree.XMLSyntaxError, IndexError) as e:
        raise ValueError('No 10-K forms found in SEC database for "{}"'.format(ticker)) from e


def get_filing_url(filing_node):
    return filing_node.xpath('./filinghref/text()')[0]


def get_xbrl_url(filing_node):
    return filing_node.xpath('./xbrlref/text()')[0]


def get_cash_flows_report_id(xbrl_url):
    resp = requests.get(xbrl_url)
    try:
        tree = html.fromstring(resp.content)
    except etree.XMLSyntaxError as e:
        raise ValueError('Invalid 10-K filing url: {}'.format(xbrl_url)) from e

    fin_stmts_menu = tree.xpath('//a[@id=\'menu_cat2\']/..')[0]
    fin_stmts = fin_stmts_menu.xpath('./ul/li/a/text()')
    try:
        cash_flows_idx = next((i for i, n in enumerate(fin_stmts) if 'cash flows' in n.lower()))
    except StopIteration:
        raise ValueError('No "Cash Flows" statement found at {}'.format(xbrl_url))

    return fin_stmts_menu.xpath('./ul/li/@id')[cash_flows_idx]


def get_cash_flows_report_url(filing_url, report_id):
    return '{}/{}.htm'.format(filing_url.rsplit('/', 1)[0], report_id.upper())


def get_cash_flows_table(cash_flows_report_url):
    resp = requests.get(cash_flows_report_url)
    try:
        tree = html.fromstring(resp.content)
    except etree.XMLSyntaxError as e:
        raise ValueError(
            'Could not parse html from url: {}'.format(cash_flows_report_url)
        ) from e

    table = tree.xpath('//table[@class=\'report\']')[0]

    return table


def cash_flows_html_to_string(table_node):
    for n in table_node.iter():
        n.attrib.pop('class', None)
        n.attrib.pop('href', None)
        n.attrib.pop('onClick', None)

    return str(etree.tostring(table_node)).replace('\\n', '').replace('b\'', '')


@require_GET
def view_report(request, pk=None):
    report = get_object_or_404(Report, pk=pk)
    stmts = list(report.statements.all())

    return render(request, 'report.html', {'report': report, 'statements': stmts})


@require_GET
def view_detail(request, pk, ticker_symbol=None):
    stmt = get_object_or_404(
        CashFlowsStatement, report__pk=pk, ticker_symbol=ticker_symbol
    )

    return render(request, 'detail.html', {'ticker_symbol': ticker_symbol, 'data': stmt.data})
