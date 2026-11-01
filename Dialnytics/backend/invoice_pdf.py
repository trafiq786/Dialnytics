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

# Page = the Dialnytics letterhead image (aspect kept, so nothing is stretched).
W = 595.27
LH_W, LH_H = 1102, 1427
H = W * LH_H / LH_W
KX = W / LH_W                      # image pixel -> pt
STATUS_COLORS = {'paid': ('#d1fae5', '#065f46'), 'sent': ('#dbeafe', '#1e40af'),
                 'draft': ('#f3f4f6', '#374151'), 'void': ('#fee2e2', '#991b1b')}
PURPLE = colors.HexColor('#5b2ee0')
HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(os.path.dirname(HERE), 'frontend', 'static')
LETTERHEAD = os.path.join(STATIC, 'img', 'letterhead.png')
CONTACT_PHONE = os.getenv('INVOICE_PHONE', '+44 7476 629105')
METHOD_LABELS = {'bank': 'Bank transfer', 'card': 'Card', 'usdt': 'Crypto (USDT)', 'other': 'Other'}

_fonts = {}


def _font(name, file, fallback):
    if name in _fonts:
        return _fonts[name]
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        pdfmetrics.registerFont(TTFont(name, os.path.join(STATIC, 'fonts', file)))
        _fonts[name] = name
    except Exception:
        _fonts[name] = fallback
    return _fonts[name]


def _fit_lines(text, font, size, width):
    """Wrap text into at most 2 lines that fit `width`; shrink the size if needed."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    words = (text or '').split()
    while size >= 5.2:
        lines, cur = [], ''
        for w in words:
            trial = (cur + ' ' + w).strip()
            if stringWidth(trial, font, size) <= width or not cur:
                cur = trial
            else:
                lines.append(cur); cur = w
        lines.append(cur)
        if len(lines) <= 2 and all(stringWidth(l, font, size) <= width for l in lines):
            return lines, size
        size -= 0.4
    return [(text or '')[:22]], 5.2


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
        if os.path.exists(LETTERHEAD):
            canvas.drawImage(LETTERHEAD, 0, 0, width=W, height=H)
        reg = _font('P-R', 'Poppins-Regular.ttf', 'Helvetica')
        med = _font('P-M', 'Poppins-Medium.ttf', 'Helvetica-Bold')
        bold = _font('P-B', 'Poppins-Bold.ttf', 'Helvetica-Bold')
        # Header strip: the proprietor / address blocks were removed from the letterhead image.
        # Customer name goes where the proprietor's name was; the phone is ours.
        ink, gray = colors.HexColor('#0f1a44'), colors.HexColor('#4b5273')
        x_name, x_phone = 82 * KX, 276 * KX
        canvas.setFillColor(gray); canvas.setFont(reg, 6.6)
        canvas.drawString(x_name, H - 254 * KX, 'Billed To')
        canvas.drawString(x_phone, H - 254 * KX, 'Phone / WhatsApp')
        lines, size = _fit_lines(str(inv.get('customer_name') or ''), med, 7.3, 118 * KX)
        canvas.setFillColor(ink); canvas.setFont(med, size)
        y0 = H - 275 * KX if len(lines) == 1 else H - 270 * KX
        for ln in lines:
            canvas.drawString(x_name, y0, ln); y0 -= size + 1.2
        canvas.setFont(med, 7.5)
        canvas.drawString(x_phone, H - 275 * KX, CONTACT_PHONE)
        # title row
        canvas.setFillColor(PURPLE); canvas.setFont(bold, 20)
        canvas.drawString(40, H - 194, 'INVOICE')
        canvas.setFillColor(gray); canvas.setFont(reg, 8.5)
        canvas.drawString(40, H - 207, str(inv.get('invoice_number') or ''))
        bg, fg = STATUS_COLORS.get(status, STATUS_COLORS['draft'])
        label = status.upper()
        canvas.setFont(med, 8)
        tw = canvas.stringWidth(label, med, 8) + 20
        canvas.setFillColor(colors.HexColor(bg))
        canvas.roundRect(W - 40 - tw, H - 202, tw, 17, 8.5, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor(fg))
        canvas.drawCentredString(W - 40 - tw / 2, H - 197, label)
        # PAID stamp
        if status == 'paid':
            canvas.saveState()
            canvas.translate(175, 318)
            canvas.rotate(14)
            canvas.setStrokeColor(colors.HexColor('#10b981')); canvas.setFillColor(colors.HexColor('#10b981'))
            canvas.setLineWidth(3)
            canvas.setFillAlpha(0.5); canvas.setStrokeAlpha(0.6)
            canvas.roundRect(-74, -25, 148, 50, 9, fill=0, stroke=1)
            canvas.setFont(bold, 30)
            canvas.drawCentredString(0, -11, 'PAID')
            canvas.restoreState()
        canvas.setFillColor(colors.HexColor('#6b7280')); canvas.setFont(reg, 7)
        canvas.drawRightString(W - 40, 172, 'Page %d' % doc.page)
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=(W, H), leftMargin=40, rightMargin=40, topMargin=216, bottomMargin=164,
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
    det.setStyle(TableStyle([('BOTTOMPADDING', (0, 0), (-1, -1), 3), ('TOPPADDING', (0, 0), (-1, -1), 3),
                             ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                             ('LINEBELOW', (0, 0), (-1, -2), 0.5, LINE)]))
    cards = Table([[bill, [Paragraph('INVOICE DETAILS', lab), det]]], colWidths=[270, 245])
    cards.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BACKGROUND', (0, 0), (-1, -1), SOFT),
                               ('BOX', (0, 0), (0, 0), 0.6, LINE), ('BOX', (1, 0), (1, 0), 0.6, LINE),
                               ('LEFTPADDING', (0, 0), (-1, -1), 14), ('RIGHTPADDING', (0, 0), (-1, -1), 14),
                               ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                               ('LINEAFTER', (0, 0), (0, 0), 8, colors.white)]))
    story += [cards, Spacer(1, 12)]

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
                           ('TOPPADDING', (0, 1), (-1, -1), 7), ('BOTTOMPADDING', (0, 1), (-1, -1), 7),
                           ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                           ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, SOFT]),
                           ('LINEBELOW', (0, 1), (-1, -1), 0.5, LINE)]))
    story += [t, Spacer(1, 8)]

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
    totals.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -3), 0.5, LINE), ('TOPPADDING', (0, 0), (-1, -1), 4),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 4), ('BACKGROUND', (0, -1), (-1, -1), PURPLE),
                                ('TOPPADDING', (0, -1), (-1, -1), 7), ('BOTTOMPADDING', (0, -1), (-1, -1), 7),
                                ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    wrap = Table([['', totals]], colWidths=[280, 235])
    wrap.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))
    story += [wrap, Spacer(1, 12)]

    # how to pay: bank details ONLY on bank-transfer invoices
    method = str(inv.get('payment_method') or 'bank').lower()
    box_style = [('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#d9d2fb')),
                 ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f6ff')),
                 ('LINEBEFORE', (0, 0), (0, -1), 4, PURPLE),
                 ('LEFTPADDING', (0, 0), (-1, -1), 14), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                 ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8)]
    ph = ParagraphStyle('ph', parent=lab, textColor=PURPLE, fontSize=8)
    if method == 'card':
        card = str(inv.get('card_name') or '').strip() or 'Card'
        rows = [[Paragraph('Payment method', tl), Paragraph('<b>Card</b>', val)],
                [Paragraph('Card', tl), Paragraph('<b>%s</b>' % _e(card), val)]]
        if inv.get('renewal_date'):
            rows.append([Paragraph('Renewal date', tl), Paragraph('<b>%s</b>' % _e(_date(inv.get('renewal_date'))), val)])
        head_txt = 'PAYMENT RECEIVED · CARD' if status == 'paid' else 'PAYMENT · CARD'
        foot = None
    elif method == 'bank':
        b = bank_details()
        rows = [[Paragraph('Account name', tl), Paragraph('<b>%s</b>' % _e(b['name']), val)],
                [Paragraph('Bank', tl), Paragraph('<b>%s</b>' % _e(b['bank']), val)],
                [Paragraph('Account number', tl), Paragraph('<b>%s</b>' % _e(b['number']), ParagraphStyle('an', parent=val, fontSize=11))]]
        head_txt = 'HOW TO PAY · BANK TRANSFER'
        foot = 'Use %s as the payment reference and send the receipt to us on WhatsApp.' % (inv.get('invoice_number') or 'the invoice number')
    else:
        rows = [[Paragraph('Payment method', tl), Paragraph('<b>%s</b>' % _e(METHOD_LABELS.get(method, method.title())), val)],
                [Paragraph('Reference', tl), Paragraph(_e(inv.get('invoice_number')), val)]]
        head_txt = 'PAYMENT · ' + METHOD_LABELS.get(method, method.title()).upper()
        foot = 'Payment details are shared with you on WhatsApp: %s' % CONTACT_PHONE
    pay = Table(rows, colWidths=[100, 380])
    pay.setStyle(TableStyle([('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                             ('LEFTPADDING', (0, 0), (-1, -1), 0)]))
    inner = [Paragraph(_e(head_txt), ph), Spacer(1, 3), pay]
    if foot and status != 'paid':
        inner += [Spacer(1, 4), Paragraph(_e(foot), small)]
    paybox = Table([[inner]], colWidths=[515])
    paybox.setStyle(TableStyle(box_style))
    if status != 'void':
        story += [KeepTogether([paybox]), Spacer(1, 10)]

    tiny = ParagraphStyle('tiny', parent=small, fontSize=8, leading=10.5)
    bits = []
    for title, key in (('Notes', 'notes'), ('Terms', 'terms')):
        text = str(inv.get(key) or '').strip()
        if text and not (key == 'terms' and status == 'paid'):
            bits.append('<b>%s:</b> %s' % (title, _e(text).replace('\n', ' ')))
    if bits:
        story += [Paragraph('  &nbsp;·&nbsp;  '.join(bits), tiny)]

    doc.build(story, onFirstPage=page, onLaterPages=page)
    return buf.getvalue()
