"""Branded invoice PDF (A4) for Dialnytics."""
import html
import os
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

NAVY = colors.HexColor('#0b1530')
NAVY2 = colors.HexColor('#16224a')
BLUE = colors.HexColor('#2563eb')
CYAN = colors.HexColor('#06b6d4')
INK = colors.HexColor('#111827')
MUTED = colors.HexColor('#6b7280')
LINE = colors.HexColor('#e5e7eb')
SOFT = colors.HexColor('#f5f7fb')
GREEN = colors.HexColor('#059669')

W, H = 595.27, 841.89
STATUS_COLORS = {'paid': ('#d1fae5', '#065f46'), 'sent': ('#dbeafe', '#1e40af'),
                 'draft': ('#f3f4f6', '#374151'), 'void': ('#fee2e2', '#991b1b')}


def bank_details():
    """Bank account shown under "How to pay" (override in Render if it changes)."""
    return {
        'name': os.getenv('INVOICE_BANK_ACCOUNT_NAME', 'Dialnytics'),
        'bank': os.getenv('INVOICE_BANK_NAME', 'United Bank Limited (UBL)'),
        'number': os.getenv('INVOICE_BANK_ACCOUNT_NUMBER', '2180410288865'),
    }


def company_lines():
    raw = os.getenv('INVOICE_FROM_LINES', 'dialnytics.co.uk|WhatsApp: +44 7476 629105')
    return [x.strip() for x in raw.split('|') if x.strip()]


def _e(v):
    return html.escape(str(v if v is not None else ''))


def _pkr(v):
    try:
        return 'PKR {:,.0f}'.format(float(v or 0))
    except (TypeError, ValueError):
        return 'PKR 0'


def _date(d):
    try:
        return d.strftime('%d %b %Y')
    except AttributeError:
        return str(d or '')


def build_invoice_pdf(inv, items, logo_path):
    buf = BytesIO()
    status = str(inv.get('status') or 'draft').lower()

    def page(canvas, doc):
        canvas.saveState()
        # header band
        canvas.setFillColor(NAVY)
        canvas.rect(0, H - 128, W, 128, fill=1, stroke=0)
        canvas.setFillColor(NAVY2)
        canvas.circle(W - 40, H - 10, 120, fill=1, stroke=0)
        # accent stripe
        canvas.setFillColor(BLUE)
        canvas.rect(0, H - 132, W * 0.62, 4, fill=1, stroke=0)
        canvas.setFillColor(CYAN)
        canvas.rect(W * 0.62, H - 132, W * 0.38, 4, fill=1, stroke=0)
        if logo_path and os.path.exists(logo_path):
            try:
                img = ImageReader(logo_path)
                iw, ih = img.getSize()
                lw = 170
                canvas.drawImage(img, 40, H - 52 - lw * ih / iw / 2, width=lw, height=lw * ih / iw, mask='auto')
            except Exception:
                canvas.setFillColor(colors.white); canvas.setFont('Helvetica-Bold', 22)
                canvas.drawString(40, H - 62, 'DIALNYTICS')
        canvas.setFillColor(colors.HexColor('#9fb0d8'))
        canvas.setFont('Helvetica', 8.5)
        y = H - 92
        for line in company_lines():
            canvas.drawString(44, y, line); y -= 11
        canvas.setFillColor(colors.white)
        canvas.setFont('Helvetica-Bold', 30)
        canvas.drawRightString(W - 40, H - 62, 'INVOICE')
        canvas.setFont('Helvetica', 10)
        canvas.setFillColor(colors.HexColor('#c7d2fe'))
        canvas.drawRightString(W - 40, H - 80, str(inv.get('invoice_number') or ''))
        # status pill
        bg, fg = STATUS_COLORS.get(status, STATUS_COLORS['draft'])
        label = status.upper()
        canvas.setFont('Helvetica-Bold', 8.5)
        tw = canvas.stringWidth(label, 'Helvetica-Bold', 8.5) + 18
        canvas.setFillColor(colors.HexColor(bg))
        canvas.roundRect(W - 40 - tw, H - 106, tw, 16, 8, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor(fg))
        canvas.drawCentredString(W - 40 - tw / 2, H - 101, label)
        # PAID stamp
        if status == 'paid':
            canvas.saveState()
            canvas.translate(W - 150, 190)
            canvas.rotate(18)
            canvas.setStrokeColor(colors.HexColor('#10b981')); canvas.setFillColor(colors.HexColor('#10b981'))
            canvas.setLineWidth(3)
            canvas.setFillAlpha(0.45); canvas.setStrokeAlpha(0.55)
            canvas.roundRect(-78, -26, 156, 52, 9, fill=0, stroke=1)
            canvas.setFont('Helvetica-Bold', 34)
            canvas.drawCentredString(0, -12, 'PAID')
            canvas.restoreState()
        # footer
        canvas.setStrokeColor(LINE); canvas.setLineWidth(0.8)
        canvas.line(40, 52, W - 40, 52)
        canvas.setFillColor(MUTED); canvas.setFont('Helvetica', 8)
        canvas.drawString(40, 38, 'Thank you for choosing Dialnytics.')
        canvas.drawRightString(W - 40, 38, '%s  ·  Page %d' % (inv.get('invoice_number') or '', doc.page))
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=(W, H), leftMargin=40, rightMargin=40, topMargin=160, bottomMargin=70,
                            title=str(inv.get('invoice_number') or 'Invoice'), author='Dialnytics')
    lab = ParagraphStyle('lab', fontName='Helvetica-Bold', fontSize=7.5, textColor=MUTED, leading=10, spaceAfter=3)
    val = ParagraphStyle('val', fontName='Helvetica', fontSize=9.5, textColor=INK, leading=13.5)
    valb = ParagraphStyle('valb', parent=val, fontName='Helvetica-Bold', fontSize=11.5, leading=15)
    cell = ParagraphStyle('cell', fontName='Helvetica', fontSize=9.5, textColor=INK, leading=13)
    cellr = ParagraphStyle('cellr', parent=cell, alignment=TA_RIGHT)
    head = ParagraphStyle('head', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white, leading=10)
    headr = ParagraphStyle('headr', parent=head, alignment=TA_RIGHT)
    small = ParagraphStyle('small', fontName='Helvetica', fontSize=8.8, textColor=colors.HexColor('#374151'), leading=13)

    story = []
    # Bill to / details cards
    bill = [Paragraph('BILL TO', lab), Paragraph(_e(inv.get('customer_name')), valb)]
    for k in ('customer_email', 'contact_phone', 'contact_address'):
        if inv.get(k):
            bill.append(Paragraph(_e(inv.get(k)), val))
    det_rows = [('Invoice number', inv.get('invoice_number')), ('Issue date', _date(inv.get('issue_date'))),
                ('Due date', _date(inv.get('due_date'))), ('Amount paid' if status == 'paid' else 'Amount due', _pkr(inv.get('total_pkr')))]
    det = Table([[Paragraph(_e(a), ParagraphStyle('dl', parent=val, textColor=MUTED, fontSize=9)),
                  Paragraph('<b>%s</b>' % _e(b), ParagraphStyle('dr', parent=val, alignment=TA_RIGHT))] for a, b in det_rows],
                colWidths=[95, 135])
    det.setStyle(TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 4), ('TOPPADDING', (0, 0), (-1, -1), 4),
                             ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                             ('LINEBELOW', (0, 0), (-1, -2), 0.5, LINE)]))
    cards = Table([[bill, [Paragraph('INVOICE DETAILS', lab), det]]], colWidths=[270, 245])
    cards.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BACKGROUND', (0, 0), (-1, -1), SOFT),
                               ('BOX', (0, 0), (0, 0), 0.6, LINE), ('BOX', (1, 0), (1, 0), 0.6, LINE),
                               ('LEFTPADDING', (0, 0), (-1, -1), 14), ('RIGHTPADDING', (0, 0), (-1, -1), 14),
                               ('TOPPADDING', (0, 0), (-1, -1), 12), ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                               ('LINEAFTER', (0, 0), (0, 0), 8, colors.white)]))
    story += [cards, Spacer(1, 22)]

    # items
    rows = [[Paragraph('#', head), Paragraph('DESCRIPTION', head), Paragraph('QTY', headr),
             Paragraph('UNIT PRICE', headr), Paragraph('AMOUNT', headr)]]
    for n, it in enumerate(items, 1):
        rows.append([Paragraph(str(n), ParagraphStyle('n', parent=cell, textColor=MUTED)), Paragraph(_e(it.get('description')), cell),
                     Paragraph(_e(it.get('qty')), cellr), Paragraph(_pkr(it.get('unit_price_pkr')), cellr),
                     Paragraph('<b>%s</b>' % _pkr(it.get('amount_pkr')), cellr)])
    t = Table(rows, colWidths=[24, 251, 45, 95, 100], repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), NAVY), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                           ('TOPPADDING', (0, 0), (-1, 0), 9), ('BOTTOMPADDING', (0, 0), (-1, 0), 9),
                           ('TOPPADDING', (0, 1), (-1, -1), 10), ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
                           ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                           ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, SOFT]),
                           ('LINEBELOW', (0, 1), (-1, -1), 0.5, LINE)]))
    story += [t, Spacer(1, 14)]

    # totals
    tot = [['Subtotal', _pkr(inv.get('subtotal_pkr'))]]
    if float(inv.get('discount_pkr') or 0):
        tot.append(['Discount', '- ' + _pkr(inv.get('discount_pkr'))])
    if float(inv.get('tax_pkr') or 0) or float(inv.get('tax_percent') or 0):
        tot.append(['Tax (%s%%)' % ('{:g}'.format(float(inv.get('tax_percent') or 0))), _pkr(inv.get('tax_pkr'))])
    tl = ParagraphStyle('tl', parent=val, textColor=MUTED)
    tr = ParagraphStyle('tr', parent=val, alignment=TA_RIGHT)
    trows = [[Paragraph(a, tl), Paragraph(b, tr)] for a, b in tot]
    due_label = 'TOTAL PAID' if status == 'paid' else 'TOTAL DUE'
    trows.append([Paragraph('<font color="white"><b>%s</b></font>' % due_label, ParagraphStyle('x', parent=val, fontSize=10)),
                  Paragraph('<font color="white"><b>%s</b></font>' % _pkr(inv.get('total_pkr')),
                            ParagraphStyle('y', parent=val, alignment=TA_RIGHT, fontSize=13, leading=16))])
    totals = Table(trows, colWidths=[110, 125])
    totals.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -3), 0.5, LINE), ('TOPPADDING', (0, 0), (-1, -1), 6),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 6), ('BACKGROUND', (0, -1), (-1, -1), BLUE),
                                ('TOPPADDING', (0, -1), (-1, -1), 10), ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
                                ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    wrap = Table([['', totals]], colWidths=[280, 235])
    wrap.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    story += [wrap, Spacer(1, 24)]

    # how to pay
    b = bank_details()
    pay_rows = [[Paragraph('Account name', tl), Paragraph('<b>%s</b>' % _e(b['name']), val)],
                [Paragraph('Bank', tl), Paragraph('<b>%s</b>' % _e(b['bank']), val)],
                [Paragraph('Account number', tl), Paragraph('<b>%s</b>' % _e(b['number']), ParagraphStyle('an', parent=val, fontSize=11))],
                [Paragraph('Reference', tl), Paragraph(_e(inv.get('invoice_number')), val)]]
    pay = Table(pay_rows, colWidths=[100, 380])
    pay.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                             ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
    paybox = Table([[[Paragraph('HOW TO PAY · BANK TRANSFER', ParagraphStyle('ph', parent=lab, textColor=BLUE, fontSize=8)), Spacer(1, 4), pay,
                      Spacer(1, 6), Paragraph('Please use the invoice number as the payment reference and send the receipt to us on WhatsApp.', small)]]],
                   colWidths=[515])
    paybox.setStyle(TableStyle([('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#c7d2fe')),
                                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f7ff')),
                                ('LINEBEFORE', (0, 0), (0, -1), 4, BLUE),
                                ('LEFTPADDING', (0, 0), (-1, -1), 16), ('RIGHTPADDING', (0, 0), (-1, -1), 14),
                                ('TOPPADDING', (0, 0), (-1, -1), 12), ('BOTTOMPADDING', (0, 0), (-1, -1), 12)]))
    if status != 'void':
        story += [KeepTogether([paybox]), Spacer(1, 18)]

    for title, key in (('NOTES', 'notes'), ('TERMS', 'terms')):
        text = str(inv.get(key) or '').strip()
        if text:
            story += [KeepTogether([Paragraph(title, lab), Paragraph(_e(text).replace('\n', '<br/>'), small)]), Spacer(1, 12)]

    doc.build(story, onFirstPage=page, onLaterPages=page)
    return buf.getvalue()
