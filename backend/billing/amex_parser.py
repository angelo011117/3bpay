import re
from decimal import Decimal,InvalidOperation
from html import unescape
from html.parser import HTMLParser
class Text(HTMLParser):
 def __init__(self):super().__init__();self.parts=[]
 def handle_data(self,d):self.parts.append(d)
def parse_amex_zelle(html):
 p=Text();p.feed(html or '');text=re.sub(r'\s+',' ',unescape(' '.join(p.parts))).strip()
 if 'Zelle' not in text or 'payment has been deposited' not in text:raise ValueError('Unsupported notification format')
 def field(label,next_label):
  m=re.search(label+r'\s*:?\s*(.+?)\s*(?='+next_label+r'\s*:|$)',text,re.I);return m.group(1).strip() if m else ''
 amount=field('Amount','From');payer=field('From','Account');account=field('Account','Transaction ID');m=re.search(r'Transaction ID\s*:?\s*(.+?)(?=\s+To view|$)',text,re.I);tx=m.group(1).strip() if m else ''
 value=re.sub(r'[^0-9.]','',amount)
 try:amount=Decimal(value).quantize(Decimal('0.01'))
 except (InvalidOperation,ValueError):raise ValueError('Invalid Amount')
 if not payer or not account or not tx:raise ValueError('Required AmEx fields missing')
 return {'amount':amount,'payer_name':payer,'recipient_account':account[-4:],'transaction_id':tx,'evidence':text[:1000]}
