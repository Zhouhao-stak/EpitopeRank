"""Capture the step-by-step tutorial screenshots from the running web UI.

Usage:  python scripts/shoot_tutorial_shots.py [base_url] [out_dir]

Requires the service to be running (python serve_ui.py --port 8800) and
Playwright with a local Chrome install (channel="chrome"). The screenshots land
in ``out/tutorial_shots/`` and are embedded by ``docs/手把手教程.html``.
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8800/"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/tutorial_shots")
OUT.mkdir(parents=True, exist_ok=True)
DEMO_PROJECT = "run_input_wild"


def shot(page: Page, name: str, wait: int = 700) -> None:
    page.wait_for_timeout(wait)
    target = OUT / name
    page.screenshot(path=str(target))
    print("saved", target)


def centre(page: Page, selector: str) -> None:
    """Scroll an element to the middle of the viewport (screenshots, not tests)."""
    page.evaluate(
        "sel => { const el = document.querySelector(sel);"
        " if (el) el.scrollIntoView({block: 'center'}); }",
        selector,
    )
    page.wait_for_timeout(700)


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 920})
        page.goto(BASE, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)

        # 01 仪表盘（已选中演示项目）
        page.fill("#project-search", DEMO_PROJECT)
        page.wait_for_timeout(400)
        shot(page, "01_dashboard.png")

        # 02 新建分析弹窗
        page.click("text=+ 新建分析")
        page.wait_for_selector("#upload-modal", state="visible", timeout=8000)
        page.fill("#project-name", "pDC活化_剪接新抗原")
        page.fill("#analysis-query", "pDC 活化后可变剪接变化")
        shot(page, "02_new_project_modal.png")
        page.evaluate("closeUploadModal()")
        page.wait_for_timeout(500)

        # 03 项目详情（点历史项目）
        page.fill("#project-search", DEMO_PROJECT)
        page.wait_for_timeout(300)
        page.click("#recent-projects >> text=" + DEMO_PROJECT)
        page.wait_for_timeout(2500)
        centre(page, "#project-detail")
        shot(page, "03_project_detail.png")

        # 04 事件浏览器
        page.click('.nav-item[data-page="explorer"]')
        page.wait_for_timeout(2200)
        shot(page, "04_explorer.png", wait=1200)

        # 05 可视化（图表目录）
        page.click('.nav-item[data-page="visualization"]')
        page.wait_for_timeout(2000)
        shot(page, "05_visualization.png", wait=1200)

        # 06 渲染一张火山图
        page.click("text=ΔPSI 瀑布图 Waterfall")
        page.wait_for_timeout(4000)
        shot(page, "06_waterfall.png", wait=1500)

        # 07 剪接候选新抗原：进入页面自动检查
        page.click('.nav-item[data-page="neoantigen"]')
        page.wait_for_timeout(3000)
        shot(page, "07_neoantigen_checked.png", wait=1500)

        # 08 列映射面板 + HLA 输入
        centre(page, "#neo-mapping-panel")
        shot(page, "08_mapping_panel.png", wait=500)

        # 09 填 HLA
        page.fill("#neo-hla", "HLA-A*02:01,HLA-B*07:02")
        shot(page, "09_hla_filled.png", wait=400)

        # 10 生成候选肽 → 结果摘要
        page.click("#neo-guided-run")
        page.wait_for_selector("#neo-result-panel", state="visible", timeout=180000)
        page.wait_for_timeout(2500)
        centre(page, "#neo-status")
        shot(page, "10_peptide_result.png", wait=800)

        # 11 结果面板（肽表）
        centre(page, "#neo-result-panel")
        shot(page, "11_result_panel.png", wait=800)

        # 12 肽预测页
        page.click('.nav-item[data-page="peptide"]')
        page.wait_for_timeout(2500)
        shot(page, "12_peptide_page.png", wait=1200)

        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
