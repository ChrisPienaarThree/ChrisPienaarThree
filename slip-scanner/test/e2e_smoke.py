"""End-to-end smoke test for src/slip-scanner.html in headless Chromium.
Usage: LIBS=/path/to/npm-packages python3 e2e_smoke.py
LIBS must hold the unpacked npm packages pdf-lib-1.17.1, jszip-3.10.1, xlsx-0.18.5, pdfjs-dist-3.11.174
(the page loads these from cdnjs in production; here they are served locally)."""
import os, io, json, base64, zipfile, math, random, sys, pathlib
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
SRC = (HERE.parent / 'src' / 'slip-scanner.html').read_text()
LIBS = pathlib.Path(os.environ['LIBS'])
OUT = pathlib.Path(os.environ.get('OUT', HERE / '_out')); OUT.mkdir(exist_ok=True)
ROUTES = {
 'pdf.js/3.11.174/pdf.min.js': LIBS/'pdfjs-dist-3.11.174/package/build/pdf.min.js',
 'pdf.js/3.11.174/pdf.worker.min.js': LIBS/'pdfjs-dist-3.11.174/package/build/pdf.worker.min.js',
 'pdf-lib/1.17.1/pdf-lib.min.js': LIBS/'pdf-lib-1.17.1/package/dist/pdf-lib.min.js',
 'jszip/3.10.1/jszip.min.js': LIBS/'jszip-3.10.1/package/dist/jszip.min.js',
 'xlsx/0.18.5/xlsx.full.min.js': LIBS/'xlsx-0.18.5/package/dist/xlsx.full.min.js'}

def font(sz):
    for f in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/dejavu/DejaVuSans.ttf']:
        if os.path.exists(f): return ImageFont.truetype(f, sz)
    return ImageFont.load_default()

def slip(w, h, title, total):
    im = Image.new('RGB', (w, h), (250, 250, 247)); d = ImageDraw.Draw(im)
    d.text((40, 40), title, fill=(10, 10, 10), font=font(44))
    for i in range(10): d.text((40, 130+i*52), f'Item {i+1}  diesel 50.0 L        R {random.randint(50,400)}.00', fill=(30, 30, 30), font=font(30))
    d.text((40, h-120), f'TOTAL INCL VAT  R {total}', fill=(0, 0, 0), font=font(40))
    return im

# 1. a phone photo: tilted white slip on a dark desk
random.seed(3)
paper = slip(700, 1000, 'ENGEN MIDDELBURG  Tax Invoice INV-889', '845.50').convert('RGBA')
bg = Image.new('RGBA', (1500, 1500), (46, 40, 36, 255))
rot = paper.rotate(9, expand=True, resample=Image.BICUBIC)
bg.alpha_composite(rot, (350, 150)); bg.convert('RGB').save(OUT/'photo.jpg', quality=90)
# 2. an Adobe-Scan-like image PDF with two different slips
a = slip(1240, 1754, 'SPAR Middelburg Till slip', '312.40'); b = slip(1240, 1754, 'Builders Warehouse INV-77', '1299.00')
a.save(OUT/'scan_two_pages.pdf', save_all=True, append_images=[b], resolution=150)

errors = []
INIT = """
window.__saved=[]; window.__prompts=[];
window.claude={use:async n=>{
  if(n==='sample'){const f=async()=>({});f.limits=async()=>({maxPromptBytes:262144,images:{maxCount:4,maxInputBytes:2e7,mediaTypes:['image/jpeg']}});
    f.json=async(p,o)=>{window.__prompts.push({p,n:(o.images||[]).length});return {docType:'Tax invoice',supplier:'Engen Middelburg',invoiceNo:'INV-889',invoiceDate:'21/10/2026',subtotal:735.22,vat:110.28,total:845.5,payment:'Card',cardLast4:'4417',description:'Diesel 50 L',category:'Fuel',confidence:.92,notes:''};};
    return f;}
  if(n==='downloads')return {save:async({filename,data})=>{const buf=new Uint8Array(await new Response(data).arrayBuffer());let s='';for(let i=0;i<buf.length;i+=8192)s+=String.fromCharCode.apply(null,buf.subarray(i,i+8192));window.__saved.push({filename,b64:btoa(s)});return {status:'saved'};}};
  return null;}};
"""
with sync_playwright() as p:
    br = p.chromium.launch()
    ctx = br.new_context(viewport={'width': 420, 'height': 900}, color_scheme='light')
    ctx.add_init_script(INIT)
    page = ctx.new_page()
    page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
    page.on('console', lambda m: errors.append('console.error: ' + m.text) if m.type == 'error' and 'fonts.g' not in m.text and 'ERR_FAILED' not in m.text else None)
    def route(r):
        u = r.request.url
        for k, f in ROUTES.items():
            if u.endswith(k): return r.fulfill(path=str(f), content_type='application/javascript')
        if 'fonts.g' in u: return r.abort()
        r.continue_()
    ctx.route('**/*', route)
    f = OUT/'page.html'
    f.write_text('<!doctype html><html><head><meta charset="utf8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light}body{margin:0;font:14px system-ui}</style></head><body>' + SRC + '</body></html>')
    page.goto('file://' + str(f)); page.wait_for_timeout(500)
    assert page.evaluate('typeof pdfjsLib!=="undefined"&&typeof PDFLib!=="undefined"&&typeof JSZip!=="undefined"&&typeof XLSX!=="undefined"'), 'libs not loaded'
    page.screenshot(path=str(OUT/'01_empty.png'))

    page.set_input_files('#inFiles', [str(OUT/'photo.jpg'), str(OUT/'scan_two_pages.pdf')])
    page.wait_for_function('document.querySelectorAll("#queue .card").length===2', timeout=60000)
    page.wait_for_selector('#busy', state='hidden', timeout=60000)
    cards = page.locator('#queue .card'); print('cards after import:', cards.count())
    thumb = page.evaluate('[...document.querySelectorAll("#queue .card")].map(c=>[...c.querySelectorAll("img")].map(i=>[i.naturalWidth,i.naturalHeight]))')
    print('thumb sizes (w,h):', thumb)
    # photo auto-crop should give a portrait page close to 0.7 aspect, not the 1:1 source
    pw, ph = thumb[0][0]; print('photo crop aspect', round(pw/ph, 2)); assert 0.55 < pw/ph < 0.85, 'auto-crop did not isolate the slip'
    page.screenshot(path=str(OUT/'02_import.png'), full_page=True)

    page.get_by_role('button', name='Split into 2 invoices').click()
    page.wait_for_function('document.querySelectorAll("#queue .card").length===3', timeout=30000)
    print('cards after split:', page.locator('#queue .card').count())

    # editor on the photo
    page.locator('#queue .card').first.locator('button.thumb').click()
    page.wait_for_selector('#editor:not([hidden])'); page.wait_for_timeout(400)
    page.get_by_role('button', name='Document', exact=True).click(); page.wait_for_timeout(500)
    page.screenshot(path=str(OUT/'03_editor_document.png'))
    page.get_by_role('button', name='Rotate right').click(); page.wait_for_timeout(500)
    page.get_by_role('button', name='Rotate left').click(); page.wait_for_timeout(500)
    page.click('#edDone'); page.wait_for_selector('#editor', state='hidden', timeout=20000)

    # analyse all (fake Claude)
    page.click('#btnAnalyse')
    page.wait_for_selector('#tab-review:not([hidden])', timeout=60000)
    prompts = page.evaluate('window.__prompts'); print('analysis calls:', len(prompts), 'images each:', [x['n'] for x in prompts])
    assert len(prompts) == 3
    page.wait_for_timeout(300); page.screenshot(path=str(OUT/'04_review.png'), full_page=True)
    first = page.locator('#reviewList .card').first
    print('review supplier:', first.locator('input[id$=-supplier]').input_value(), '| total:', first.locator('input[id$=-total]').input_value(), '| date:', first.locator('input[id$=-invoiceDate]').input_value())
    print('check chips:', [c.inner_text() for c in first.locator('.checks .chip').all()])
    # make the 2nd doc different so it is not a duplicate; the 3rd stays a duplicate of the 1st
    cs = page.locator('#reviewList .card')
    cs.nth(1).locator('input[id$=-supplier]').fill('SPAR Middelburg'); cs.nth(1).locator('input[id$=-total]').fill('312.40'); cs.nth(1).locator('input[id$=-invoiceNo]').fill('')
    cs.nth(2).locator('input[id$=-supplier]').fill('Builders Warehouse'); cs.nth(2).locator('input[id$=-total]').fill('1299'); cs.nth(2).locator('input[id$=-invoiceNo]').fill('INV-77')
    print('dup chip on #1 absent:', not any('duplicate' in c.inner_text() for c in cs.nth(0).locator('.checks .chip').all()))
    for i in range(3): cs.nth(i).get_by_role('button', name='Approve').click()
    page.wait_for_function('document.querySelector("#btnFile").textContent.includes("3")')
    page.click('#btnFile')
    page.wait_for_selector('#tab-register:not([hidden])', timeout=60000); page.wait_for_selector('#batch:not([hidden])')
    page.wait_for_timeout(300); page.screenshot(path=str(OUT/'05_register.png'), full_page=True)
    print('register rows:', page.locator('#tbody tr').count())
    page.get_by_role('button', name='Download batch (zip)').click(); page.wait_for_function('window.__saved.length>=1', timeout=30000)
    page.get_by_role('button', name='Download register (xlsx)').click(); page.wait_for_function('window.__saved.length>=2', timeout=30000)
    saved = page.evaluate('window.__saved')
    z = zipfile.ZipFile(io.BytesIO(base64.b64decode(saved[0]['b64']))); print('zip:', saved[0]['filename']); 
    for n in z.namelist(): print('  ', n, z.getinfo(n).file_size)
    pdfs = [n for n in z.namelist() if n.endswith('.pdf')]; assert len(pdfs) == 3 and all(z.read(n)[:5] == b'%PDF-' for n in pdfs)
    csv = [n for n in z.namelist() if n.endswith('.csv')][0]; print(z.read(csv).decode('utf-8-sig').splitlines()[0][:120])
    open(OUT/'register.xlsx', 'wb').write(base64.b64decode(saved[1]['b64'])); print('xlsx bytes:', os.path.getsize(OUT/'register.xlsx'))
    # reload: queue empty (filed), batch survives, register persisted locally
    page.reload(); page.wait_for_timeout(800); page.click('#t-register'); page.wait_for_timeout(300)
    print('after reload rows:', page.locator('#tbody tr').count(), '| batch panel visible:', page.locator('#batch').is_visible())
    # dark + desktop look
    ctx2 = br.new_context(viewport={'width': 1100, 'height': 800}, color_scheme='dark'); ctx2.add_init_script(INIT); ctx2.route('**/*', route)
    p2 = ctx2.new_page(); p2.goto('file://' + str(f)); p2.wait_for_timeout(500); p2.screenshot(path=str(OUT/'06_dark_desktop.png'))
    br.close()
print('ERRORS:', errors if errors else 'none')
