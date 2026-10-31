"""Sanitized owned-number feed for the marketing service (no purchasing)."""
import re

NANP_TOLLFREE = {'800', '833', '844', '855', '866', '877', '888'}


def normalize(number, country, provider):
    if not isinstance(number, str) or not re.fullmatch(r'\+[1-9]\d{7,14}', number):
        return None
    country = (country or '').upper()
    if country == 'UK':
        country = 'GB'
    if country not in ('US', 'CA', 'GB'):
        return None
    if provider == 'twilio' and country != 'GB':
        return None
    if provider == 'telnyx' and country not in ('US', 'CA'):
        return None
    if country == 'GB' and not number.startswith('+44'):
        return None
    if country in ('US', 'CA') and not (number.startswith('+1') and len(number) == 12):
        return None
    tollfree = country in ('US', 'CA') and number[2:5] in NANP_TOLLFREE
    return {'number': number, 'country': country, 'provider': provider,
            'type': 'toll_free' if tollfree else 'local'}


def available_rows(records, assigned):
    """Exclude any assigned number, including inactive accounts, until explicitly released."""
    seen, result = set(), []
    for record in records:
        n = normalize(record.get('number'), record.get('country'), record.get('provider'))
        if not n or n['number'] in assigned or n['number'] in seen:
            continue
        seen.add(n['number'])
        result.append(n)
    return sorted(result, key=lambda x: x['number'])
