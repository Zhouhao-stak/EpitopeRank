from pathlib import Path
from playwright.sync_api import sync_playwright

out=Path('out/demo_videos/real_screens');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
    page.goto('http://127.0.0.1:8800/',wait_until='networkidle')
    page.screenshot(path=str(out/'01_dashboard.png'))
    page.get_by_text('demo_rmats',exact=True).first.click()
    page.wait_for_timeout(700)
    page.screenshot(path=str(out/'01b_demo_project.png'))
    for idx,key in enumerate(['pipeline','explorer','visualization','gene','report','assistant','neoantigen'],2):
        page.locator(f'.nav-item[data-page="{key}"]').click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(out/f'{idx:02d}_{key}.png'))
        if key=='visualization':
            page.get_by_text('火山图 Volcano',exact=False).first.click()
            page.wait_for_timeout(1100)
            page.screenshot(path=str(out/'04b_volcano.png'))
        if key=='neoantigen':
            page.mouse.wheel(0,650)
            page.wait_for_timeout(300)
            page.screenshot(path=str(out/'08b_neoantigen_lower.png'))
    page.locator('.nav-item[data-page="dashboard"]').click()
    page.get_by_text('+ 新建分析',exact=False).first.click()
    page.wait_for_timeout(500)
    page.screenshot(path=str(out/'09_new_analysis.png'))
    browser.close()
