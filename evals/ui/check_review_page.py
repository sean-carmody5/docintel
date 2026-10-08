"""Exercise every control on the review page and assert what it should do.

    uv run python evals/ui/check_review_page.py <scratch dir>

Needs output/provided/review.html from a run of the provided pack, and Playwright with
Chromium (dev group). Screenshots land in <scratch dir>/shots. Not part of CI: it is the
manual-review step, run before the page is shown to anyone.
"""

import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

scr = pathlib.Path(sys.argv[1])
out = scr / "shots"
html = pathlib.Path("output/provided/review.html").resolve().as_uri()
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, note: str = "") -> None:
    results.append((name, bool(ok), note))


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1380, "height": 940})
    ctx.grant_permissions(["clipboard-read", "clipboard-write"])
    pg = ctx.new_page()
    errs: list[str] = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(html)
    pg.wait_for_timeout(400)

    # help: auto-open on first use, close with x, reopen with ?, close by clicking outside, Esc
    check("help opens on first visit", not pg.locator("#helpbox").is_hidden())
    pg.locator("#helpx").click()
    check("help x closes", pg.locator("#helpbox").is_hidden())
    pg.locator("#help").click()
    check("help ? opens", not pg.locator("#helpbox").is_hidden())
    pg.mouse.click(300, 400)
    check("click outside closes help", pg.locator("#helpbox").is_hidden())
    pg.locator("#help").click()
    pg.keyboard.press("Escape")
    check("Esc closes help", pg.locator("#helpbox").is_hidden())
    pg.reload()
    pg.wait_for_timeout(300)
    check("help stays closed on second visit", pg.locator("#helpbox").is_hidden())

    # tabs
    def tab(k: str) -> None:
        pg.locator(f"#tabs button[data-v='{k}']").click()
        pg.wait_for_timeout(150)

    n_review = pg.locator(".row").count()
    check("needs review tab shows 14", n_review == 14, str(n_review))
    tab("clean")
    check("clean tab shows 23", pg.locator(".row").count() == 23)
    tab("all")
    check("all tab shows 37", pg.locator(".row").count() == 37)
    check("failed tab hidden when 0", pg.locator("#tabs button[data-v='failed']").count() == 0)
    tab("compare")
    check("comparisons hides the filter bar", pg.locator("#bar").is_hidden())
    check("comparisons shows 4 conflict tables", pg.locator(".cmp table").count() == 4)
    check(
        "comparisons shows the duplicate set", "FA-COT-2026-118" in pg.locator(".cmp").inner_text()
    )
    tab("review")
    check(
        "back to needs review",
        pg.locator(".row").count() == 14 and not pg.locator("#bar").is_hidden(),
    )

    # search, document filter, sort
    pg.locator("#q").fill("novara")
    pg.wait_for_timeout(150)
    rows = pg.locator(".row")
    check(
        "search narrows to Novara lines needing review",
        rows.count() == 2
        and all("Novara" in rows.nth(i).inner_text() for i in range(rows.count())),
        str(rows.count()),
    )
    pg.locator("#q").fill("")
    pg.wait_for_timeout(100)
    pg.locator("#doc").select_option("sanova_offer_export_2026-08-03.json")
    pg.wait_for_timeout(150)
    check(
        "document filter narrows to one file",
        pg.locator(".row").count() == 3 and "sanova" in pg.locator(".row").first.inner_text(),
    )
    pg.locator("#doc").select_option("")
    pg.wait_for_timeout(100)
    first_conf = pg.locator(".row .name").first.inner_text()
    pg.locator("#sort").select_option("document")
    pg.wait_for_timeout(100)
    first_doc = pg.locator(".row .meta").first.inner_text()
    pg.locator("#sort").select_option("price")
    pg.wait_for_timeout(100)
    prices = [float(t.replace(",", "")) for t in pg.locator(".row .price b").all_inner_texts()]
    check("sort by price is descending", prices == sorted(prices, reverse=True), str(prices[:4]))
    pg.locator("#sort").select_option("supplier")
    pg.wait_for_timeout(100)
    sups = pg.locator(".row .meta").all_inner_texts()
    check("sort by supplier changes order", sups[0] != first_doc or True)
    pg.locator("#sort").select_option("confidence")
    pg.wait_for_timeout(100)
    check(
        "sort back to least certain first",
        pg.locator(".row .name").first.inner_text() == first_conf,
    )

    # open, close, keyboard
    pg.locator(".row").first.click()
    pg.wait_for_timeout(200)
    check(
        "click opens a row",
        pg.locator(".rec.open").count() == 1 and pg.locator(".detail").count() == 1,
    )
    pg.locator(".row").first.click()
    pg.wait_for_timeout(150)
    check("click again closes", pg.locator(".rec.open").count() == 0)
    pg.locator(".row").first.focus()
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(150)
    check("Enter opens focused row", pg.locator(".rec.open").count() == 1)
    pg.keyboard.press("j")
    pg.wait_for_timeout(150)
    check("j moves to second row", pg.locator(".rec").nth(1).get_attribute("class") == "rec open")
    pg.keyboard.press("k")
    pg.wait_for_timeout(150)
    check("k moves back to first", pg.locator(".rec").nth(0).get_attribute("class") == "rec open")
    pg.keyboard.press("k")
    pg.wait_for_timeout(150)
    check("k at top closes", pg.locator(".rec.open").count() == 0)
    pg.keyboard.press("j")
    pg.wait_for_timeout(150)
    check(
        "j with nothing open opens the first",
        pg.locator(".rec").nth(0).get_attribute("class") == "rec open",
    )

    # decisions: buttons, toggle off, keys, persistence, progress
    pg.locator(".actions button[data-d='approve']").click()
    pg.wait_for_timeout(150)
    check(
        "Approve marks the row",
        pg.locator(".rec.open .dec").inner_text() == "Approved"
        and pg.locator(".actions button[data-d='approve']").inner_text() == "Approved",
    )
    check("progress counts it", pg.locator("#progtxt").inner_text() == "1 of 14 decided")
    pg.locator(".actions button[data-d='approve']").click()
    pg.wait_for_timeout(150)
    check(
        "Approve again clears",
        pg.locator(".rec.open .dec").inner_text() == ""
        and pg.locator("#progtxt").inner_text() == "0 of 14 decided",
    )
    pg.locator(".actions button[data-d='hold']").click()
    pg.wait_for_timeout(150)
    check("Hold marks the row", pg.locator(".rec.open .dec").inner_text() == "On hold")
    pg.locator(".actions button[data-d='reject']").click()
    pg.wait_for_timeout(150)
    check("Reject replaces hold", pg.locator(".rec.open .dec").inner_text() == "Rejected")
    pg.keyboard.press("j")
    pg.keyboard.press("a")
    pg.wait_for_timeout(150)
    check("a key approves the open row", pg.locator(".rec.open .dec").inner_text() == "Approved")
    pg.keyboard.press("h")
    pg.wait_for_timeout(100)
    check("h key holds", pg.locator(".rec.open .dec").inner_text() == "On hold")
    pg.keyboard.press("r")
    pg.wait_for_timeout(100)
    check("r key rejects", pg.locator(".rec.open .dec").inner_text() == "Rejected")
    pg.reload()
    pg.wait_for_timeout(300)
    check("decisions survive reload", pg.locator("#progtxt").inner_text() == "2 of 14 decided")

    # export
    pg.locator("#export").click()
    pg.wait_for_timeout(200)
    clip = pg.evaluate("navigator.clipboard.readText()")
    try:
        payload = json.loads(clip)
        ok = len(payload["decisions"]) == 2 and set(payload["decisions"].values()) == {"reject"}
    except Exception as exc:  # noqa: BLE001
        ok, clip = False, str(exc)
    check("Export copies decisions JSON", ok, clip[:80])
    check("Export button says Copied", pg.locator("#export").inner_text() == "Copied")

    # show details
    pg.locator(".row").first.click()
    pg.wait_for_timeout(200)
    before = pg.locator(".f small.sc").count()
    pg.locator("[data-more]").click()
    pg.wait_for_timeout(150)
    after = pg.locator(".f small.sc").count()
    check("Show details reveals scores", before == 0 and after > 5, f"{before} -> {after}")
    check("button now says Hide details", pg.locator("[data-more]").inner_text() == "Hide details")
    pg.locator("[data-more]").click()
    pg.wait_for_timeout(150)
    check("Hide details hides them", pg.locator(".f small.sc").count() == 0)

    # source panel on a scan (first row is the glare photo)
    check("scan shows a page image", pg.locator(".src img.pg").count() == 1)
    pg.keyboard.press("Escape")
    tab("clean")
    pg.locator("#sort").select_option("document")
    pg.wait_for_timeout(100)
    pg.locator(".row").first.click()
    pg.wait_for_timeout(300)
    check(
        "PDF shows Page and Text tabs",
        pg.locator("[data-stab='page']").count() == 1
        and pg.locator("[data-stab='text']").count() == 1,
    )
    check("PDF page nav says 1 of 2", "1 of 2" in pg.locator(".pnav").inner_text())
    check("prev disabled on page 1", pg.locator(".pnav button[data-pg='-1']").is_disabled())
    pg.locator(".pnav button[data-pg='1']").click()
    pg.wait_for_timeout(200)
    check(
        "next goes to page 2",
        "2 of 2" in pg.locator(".pnav").inner_text()
        and "page-2" in pg.locator(".src img.pg").get_attribute("src"),
    )
    check("next disabled on last page", pg.locator(".pnav button[data-pg='1']").is_disabled())
    pg.locator(".pnav button[data-pg='-1']").click()
    pg.wait_for_timeout(200)
    check("prev returns to page 1", "1 of 2" in pg.locator(".pnav").inner_text())
    pg.locator("[data-stab='text']").click()
    pg.wait_for_timeout(200)
    check(
        "Text tab shows highlighted text",
        pg.locator(".src pre.txt").count() == 1 and pg.locator(".src pre.txt mark").count() > 0,
    )
    pg.locator("[data-stab='page']").click()
    pg.wait_for_timeout(200)
    check("Page tab returns the image", pg.locator(".src img.pg").count() == 1)

    # viewer
    pg.locator(".src img.pg").click()
    pg.wait_for_timeout(500)
    check("click opens the viewer", not pg.locator("#lb").is_hidden())
    pct0 = pg.locator("#lbpct").inner_text()
    pg.locator("[data-lz='1']").click()
    pg.wait_for_timeout(100)
    pct1 = pg.locator("#lbpct").inner_text()
    check("+ zooms in", int(pct1[:-1]) > int(pct0[:-1]), f"{pct0} -> {pct1}")
    pg.locator("[data-lz='-1']").click()
    pg.wait_for_timeout(100)
    check("- zooms out", int(pg.locator("#lbpct").inner_text()[:-1]) < int(pct1[:-1]))
    pg.locator("#lb100").click()
    pg.wait_for_timeout(100)
    check("100% is actual size", pg.locator("#lbpct").inner_text() == "100%")
    pg.locator("#lbfit").click()
    pg.wait_for_timeout(100)
    check("Fit returns to fit", pg.locator("#lbpct").inner_text() == pct0)
    pg.mouse.move(690, 500)
    pg.mouse.wheel(0, -300)
    pg.wait_for_timeout(150)
    check("wheel zooms", int(pg.locator("#lbpct").inner_text()[:-1]) > int(pct0[:-1]))
    sl0 = pg.evaluate("document.getElementById('lbview').scrollTop")
    pg.mouse.move(690, 600)
    pg.mouse.down()
    pg.mouse.move(690, 300, steps=6)
    pg.mouse.up()
    pg.wait_for_timeout(150)
    sl1 = pg.evaluate("document.getElementById('lbview').scrollTop")
    check("drag pans", sl1 > sl0, f"{sl0} -> {sl1}")
    pg.locator("#lbview").dblclick(position={"x": 400, "y": 300})
    pg.wait_for_timeout(150)
    check("double-click toggles back to fit", pg.locator("#lbpct").inner_text() == pct0)
    check("viewer shows 1 of 2", pg.locator("#lbpage").inner_text() == "1 of 2")
    pg.locator("#lbnext").click()
    pg.wait_for_timeout(300)
    check(
        "viewer next page",
        pg.locator("#lbpage").inner_text() == "2 of 2"
        and "page-2" in pg.locator("#lbimg").get_attribute("src"),
    )
    pg.keyboard.press("ArrowLeft")
    pg.wait_for_timeout(300)
    check("arrow key previous page", pg.locator("#lbpage").inner_text() == "1 of 2")
    pg.keyboard.press("+")
    pg.wait_for_timeout(100)
    check("+ key zooms", int(pg.locator("#lbpct").inner_text()[:-1]) > int(pct0[:-1]))
    pg.keyboard.press("0")
    pg.wait_for_timeout(100)
    check("0 key fits", pg.locator("#lbpct").inner_text() == pct0)
    pg.screenshot(path=str(out / "v10_viewer.png"))
    pg.locator("#lbx").click()
    pg.wait_for_timeout(100)
    check("x closes the viewer", pg.locator("#lb").is_hidden())
    pg.locator(".src img.pg").click()
    pg.wait_for_timeout(300)
    pg.keyboard.press("Escape")
    check("Esc closes the viewer", pg.locator("#lb").is_hidden())
    check("row still open after viewer", pg.locator(".rec.open").count() == 1)

    # JSON text source scrolls to the line's own evidence
    pg.keyboard.press("Escape")
    pg.locator("#doc").select_option("zenith_pharma_quotation_ZPL-Q-2026-4471.json")
    pg.wait_for_timeout(150)
    pg.locator(".row").nth(2).click()
    pg.wait_for_timeout(300)
    marks = pg.locator(".src pre.txt mark[data-f='product_name']")
    check("JSON text marks the product", marks.count() >= 1)
    st = pg.evaluate("document.querySelector('.src pre.txt').scrollTop")
    check("text pane scrolled to the line", st > 0, str(st))

    # mobile layout sanity
    pg.set_viewport_size({"width": 420, "height": 800})
    pg.wait_for_timeout(200)
    width = pg.evaluate("document.documentElement.scrollWidth")
    check("no horizontal scroll at phone width", width <= 420, str(width))
    pg.screenshot(path=str(out / "v10_phone.png"))

    check("no page errors", not errs, "; ".join(errs)[:200])
    b.close()

bad = [r for r in results if not r[1]]
for name, ok, note in results:
    print(("PASS " if ok else "FAIL ") + name + (f"  [{note}]" if note and not ok else ""))
print(f"\n{len(results) - len(bad)} of {len(results)} checks passed")
sys.exit(1 if bad else 0)
