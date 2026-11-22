# Context

The portal currently uses a generic blue “EC” identity. The requested update should make it recognizably belong to 深圳北理莫斯科大学 while feeling more approachable than a formal institutional website. Use a compact official university emblem rather than the wide institutional wordmark or separate 10th-anniversary logo. Keep the existing ExtraClasses product name, routes, content, and placeholder behavior.

Official references:
- Official emblem/favicon: https://www.smbu.edu.cn/favicon.ico
- Visual identity page: https://www.smbu.edu.cn/info/1430/5907.htm
- Observed official palette: burgundy `#A70237`, pale blush `#FBF2F5`, white, and dark gray `#333333`.

# Implementation

1. **Add the official icon**
   - Create `app/static/images/` and download the official favicon as `smbu-favicon.ico`.
   - Serve it through the existing `/static` mount; no route changes are needed.

2. **Update the shared header and favicon**
   - In `app/templates/base.html`, replace the inline EC favicon with the local official icon.
   - Replace the EC text inside `.brand-mark` with the compact official emblem image. Reuse `.brand-mark`, give the image explicit dimensions and concise university alternative text, and keep the visible ExtraClasses wordmark beside it.
   - Keep the existing home link, navigation, sign-up action, and `aria-current` behavior. Do not add the wide logo or change `SITE_NAME` or `_icons.html`.

3. **Apply a softer SMBU theme in `app/static/css/style.css`**
   - Change the existing tokens to burgundy `#A70237`, darker burgundy for hover/text states, pale blush surfaces, warm off-white page background, dark gray ink, muted warm gray, and blush borders.
   - Replace remaining blue gradients, button shadows, hover borders, timetable surfaces, and date backgrounds with coordinated blush/warm-neutral values. Preserve green availability indicators and existing warning colors.
   - Use a local system font stack including Segoe UI, PingFang SC, and Microsoft YaHei; add no webfont, CDN, framework, or JavaScript.
   - Make the design less strict through modestly larger corner radii, softer low-opacity shadows, subtle blush/warm background gradients, and comfortable existing card padding rather than a layout rewrite.
   - Adapt `.brand-mark` to present the emblem cleanly on a light rounded tile, retain visible focus outlines and active-nav weight, and prevent header overflow at 390 px.

4. **Add focused smoke coverage**
   - Extend `tests/test_pages.py` to verify the shared shell references the local icon and that it returns HTTP 200 with a suitable MIME type.

# Verification

- Run `pytest` and keep all existing homepage and “Planned” placeholder assertions passing.
- Restart the local server if needed and inspect the home page plus each placeholder page at 1440 px and 390 px.
- Confirm the official icon renders crisply, navigation remains usable, no horizontal overflow appears, keyboard focus stays visible, and placeholder pages still link back to the main page.
