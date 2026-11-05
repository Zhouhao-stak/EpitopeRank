"""Render all workspaces with empty API fixtures; requires Playwright Chromium.
Run from repository root: python scripts/check_frontend.py
No live API requests or prediction jobs are submitted.
"""
from pathlib import Path
import os
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from epitoperank.interface.web_ui import render
pages=['dashboard','pipeline','explorer','visualization','gene','report','settings','neoantigen','peptide']
Path('out/ui-review').mkdir(exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True, **({'executable_path': os.environ['UI_CHROMIUM_PATH']} if os.environ.get('UI_CHROMIUM_PATH') else {}))
 page=browser.new_page(viewport={'width':1440,'height':1000})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 # 记录脚本请求，用来验证 opencc（1.1MB）确实没有在首屏被拉取。
 scripts=[]
 def on_request(r):
  if r.resource_type=='script': scripts.append(r.url)
 page.on('request',on_request)
 def route(r):
  if r.request.resource_type=='document': r.fulfill(status=200,content_type='text/html',body=render('EpitopeRank').body)
  elif r.request.resource_type=='script': r.fulfill(status=200,content_type='text/javascript',body=Path('epitoperank/interface/opencc-cn2t.js').read_text(encoding='utf8'))
  else: r.fulfill(status=200,content_type='application/json',body='{}')
 page.route('**/*',route);page.goto('http://localhost:8877');page.wait_for_timeout(400)
 assert not any('opencc' in u for u in scripts), f'opencc 不应在首屏加载: {scripts}'
 print('首屏脚本请求:',scripts or '无外部脚本')
 for width in [1440,390]:
  page.set_viewport_size({'width':width,'height':1000})
  for name in pages:
   page.evaluate('(name)=>navigateTo(name)',name);page.wait_for_timeout(350)
   page.screenshot(path=f'out/ui-review/{name}-{width}.png',full_page=True)
   overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth')
   assert not overflow, f'{name} overflows at {width}px'
   print(name,width,'overflow',overflow)
 page.locator('.mobile-menu').click();page.locator('.sidebar').wait_for(state='visible')
 assert page.evaluate("document.querySelector('main').inert")
 assert page.evaluate("getComputedStyle(document.body).overflow === 'hidden'")
 page.locator('.nav-item[data-page=peptide]').click();page.locator('.sidebar').wait_for(state='hidden')
 assert not page.evaluate("document.querySelector('main').inert")
 page.get_by_role('button',name='填入示例',exact=True).click();assert page.locator('#pep-sequences').input_value().startswith('SLYNTVATL')
 # 繁体：点击后才按需下载 opencc，下载完成后应自动补齐转换
 page.locator('.lang-toggle button[data-lang=zh-Hant]').click()
 page.wait_for_function("document.querySelector('.nav-item[data-page=dashboard]').textContent.trim() === '儀表盤'")
 assert any('opencc' in u for u in scripts), '切换繁體后应触发 opencc 加载'
 page.screenshot(path='out/ui-review/lang-zh-hant-1440.png')
 page.locator('.lang-toggle button[data-lang=zh]').click()
 page.wait_for_function("document.querySelector('.nav-item[data-page=dashboard]').textContent.trim() === '仪表盘'")
 print('繁简切换（按需加载 opencc）通过')
 page.keyboard.press('Control+k')
 assert page.locator('#quick-dialog').is_visible()
 page.locator('#quick-search').fill('报告')
 assert page.locator('.quick-result:visible').count()==1
 page.locator('.quick-result:visible').click()
 assert page.locator('#page-report').is_visible()
 page.locator('#motion-toggle').click()
 assert page.evaluate('!motionIsEnabled()')
 page.evaluate("navigateTo('gene')")
 assert page.evaluate("document.getElementById('page-gene').getAnimations().length === 0")
 page.emulate_media(reduced_motion='reduce')
 page.wait_for_function("document.getElementById('motion-toggle').disabled")
 page.emulate_media(reduced_motion='no-preference')
 page.locator('#motion-toggle').click()
 page.evaluate("navigateTo('dashboard')")
 page.keyboard.press('Control+k')
 page.wait_for_timeout(350)
 page.screenshot(path='out/ui-review/quick-switch-390.png')
 page.keyboard.press('Escape')
 assert not page.locator('#quick-dialog').is_visible()
 page.evaluate('showUploadModal()');page.screenshot(path='out/ui-review/upload-390.png',full_page=True)
 # 降级路径：opencc 拿不到时不能白屏或抛错，保持简体并给出提示
 page.unroute('**/*')
 def broken(r):
  if 'opencc' in r.request.url: r.fulfill(status=404,body='not found')
  elif r.request.resource_type=='document': r.fulfill(status=200,content_type='text/html',body=render('EpitopeRank').body)
  else: r.fulfill(status=200,content_type='application/json',body='{}')
 page.route('**/*',broken)
 page.goto('http://localhost:8877');page.wait_for_timeout(300)
 page.locator('.lang-toggle button[data-lang=zh-Hant]').click();page.wait_for_timeout(500)
 assert page.evaluate("document.querySelector('.nav-item[data-page=dashboard]').textContent.trim()") == '仪表盘'
 assert '載入失敗' in page.evaluate("Array.from(document.querySelectorAll('[role=status],[role=alert]')).map(n=>n.textContent).join('|')")
 print('opencc 加载失败时的降级路径通过')
 assert not errors, errors
 print('All 18 views, drawer, quick search, motion preferences, example interaction and zh-Hant lazy-load passed.')
 browser.close()
