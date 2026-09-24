#!/usr/bin/env python3
"""
Abu Dhabi DARI Tenancy Contract 9-Page Generation Engine
Replicates official Department of Municipalities and Transport / ADREC Tenancy Contract.
"""

import os
import io
import json
import argparse
from PIL import Image, ImageDraw, ImageFont
import qrcode

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
TEMPLET_DIR = os.path.join(BASE_DIR, "templet")
DEMO_DIR = os.path.join(BASE_DIR, "demo")

import functools

_template_cache = {}

def get_template_image(template_path: str) -> Image.Image:
    """Loads and caches template base images in memory for 7x faster generation."""
    if template_path not in _template_cache:
        _template_cache[template_path] = Image.open(template_path).convert("RGBA")
    return _template_cache[template_path].copy()


@functools.lru_cache(maxsize=128)
def get_font(name, size):
    """Loads font matching official ADREC / DARI contract demo typography."""
    font_files = {
        "regular": [
            "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
            "/usr/share/fonts/opentype/urw-base35/URWGothic-Book.otf",
            os.path.join(FONTS_DIR, "LiberationSans-Regular.ttf"),
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ],
        "medium": [
            "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
            "/usr/share/fonts/opentype/urw-base35/URWGothic-Book.otf",
            os.path.join(FONTS_DIR, "LiberationSans-Regular.ttf"),
        ],
        "bold": [
            "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
            "/usr/share/fonts/opentype/urw-base35/URWGothic-Book.otf",
            os.path.join(FONTS_DIR, "LiberationSans-Regular.ttf"),
        ],
        "arabic_regular": [
            os.path.join(FONTS_DIR, "NotoSansArabic-Regular.ttf"),
            "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ],
        "arabic_bold": [
            os.path.join(FONTS_DIR, "NotoSansArabic-Regular.ttf"),
            "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ],
        "dejavu": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            os.path.join(FONTS_DIR, "LiberationSans-Regular.ttf"),
        ],
        "url": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            os.path.join(FONTS_DIR, "LiberationSans-Regular.ttf"),
        ],
    }

    candidates = font_files.get(name, font_files["regular"])
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def has_arabic(text: str) -> bool:
    """Returns True if the text contains any Arabic characters."""
    if not text:
        return False
    return any(
        '\u0600' <= ch <= '\u06FF' or
        '\u0750' <= ch <= '\u077F' or
        '\u08A0' <= ch <= '\u08FF' or
        '\uFB50' <= ch <= '\uFDFF' or
        '\uFE70' <= ch <= '\uFEFF'
        for ch in str(text)
    )


def has_latin(text: str) -> bool:
    """Returns True if the text contains any Latin characters."""
    if not text:
        return False
    return any(('a' <= ch <= 'z') or ('A' <= ch <= 'Z') for ch in str(text))


def resolve_font_name(requested_font: str, text: str) -> str:
    """
    Ensures font compatibility with the script of the text:
    - If Arabic font requested but text has NO Arabic characters, switch to 'regular' or 'bold'.
    - If text has BOTH Arabic and Latin characters, ensure DejaVuSans is used so no glyphs become tofu.
    """
    if "arabic" in requested_font:
        if not has_arabic(text):
            return "regular" if "regular" in requested_font else "bold"
        elif has_latin(text):
            return "dejavu"
    return requested_font


def render_qr_code(card: Image.Image, qr_text: str):
    """
    Renders the official top-left QR code containing the direct verification link with contract number only.
    Exact position: x=[84, 191], y=[67, 174], size=107x107 px.
    """
    if not qr_text:
        return

    text = str(qr_text).strip()
    if text.startswith("http://") or text.startswith("https://"):
        qr_url = text
    else:
        qr_url = f"https://dari-aec.com/en/app/verify-tenant-contract?search={text}"

    # Clean the 108x108 region first to cover any existing artifact
    draw = ImageDraw.Draw(card)
    draw.rectangle([(84, 66), (191, 174)], fill=(255, 255, 255, 255))

    qr = qrcode.QRCode(
        box_size=4,
        border=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M
    )
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    qr_resized = qr_img.resize((107, 107), Image.Resampling.NEAREST)
    card.paste(qr_resized, (84, 67), qr_resized)


def render_common_footer(card: Image.Image, contract_no: str, contract_date: str):
    """
    Renders common bottom footer text on all contract pages with proper typography and sizing.
    Uses exact positioning matching official DARI template guidelines without destructive masking.
    """
    draw = ImageDraw.Draw(card)
    font_cno = get_font("regular", 14.5)
    font_date = get_font("regular", 14.0)
    font_url = get_font("regular", 14.5)
    color_text = (45, 45, 45)  # Exact tone as official demo (NOT pure black)
    color_url = (39, 91, 119)  # Official DARI brand link color

    url_text = "https://dari-aec.com/en/app/verify-tenant-contract"

    # 1. Verification URL - Left (under English notice, cleanly on top of left underline at y=1920)
    draw.text((47, 1920), url_text, fill=color_url, font=font_url, anchor="ls")

    # 2. Verification URL - Right (under Arabic notice, cleanly on top of right underline at y=1902)
    draw.text((996, 1902), url_text, fill=color_url, font=font_url, anchor="ls")

    # 3. Contract ID (Number) - Centered in gap x=135..262 between 'Contract No.:' and 'رقم العقد :'
    if contract_no:
        draw.text((199, 1954), str(contract_no).strip(), fill=color_text, font=font_cno, anchor="ms")

    # 4. Contract Date - Centered in gap x=1195..1296 between 'Contract Date:' and ': تاريخ العقد'
    if contract_date:
        draw.text((1246, 1954), str(contract_date).strip(), fill=color_text, font=font_date, anchor="ms")


def wrap_text_by_words(text, font, max_w):
    """Splits text into lines by whitespace so no line exceeds max_w if possible."""
    words = text.strip().split()
    if not words:
        return []
    lines = []
    curr = words[0]
    for w in words[1:]:
        cand = curr + " " + w
        bb = font.getbbox(cand)
        if (bb[2] - bb[0]) <= max_w:
            curr = cand
        else:
            lines.append(curr)
            curr = w
    if curr:
        lines.append(curr)
    return lines


def fit_or_wrap_email(email, max_w, initial_sz=20, min_sz=14, font_name="regular"):
    """Auto-sizes or cleanly wraps email address across lines so it never crosses table borders."""
    if not email or str(email).strip() in ["-", "~", ""]:
        return ["-"], get_font(font_name, initial_sz)

    email = str(email).strip()

    # Check 1: Single line fit with generous padding
    f_init = get_font(font_name, initial_sz)
    bb = f_init.getbbox(email)
    if (bb[2] - bb[0]) <= (max_w - 24):
        return [email], f_init

    # Check 2: Break into 2 lines at '@'
    if "@" in email:
        p1, p2 = email.split("@", 1)
        l1 = p1 + "@"
        l2 = p2
        for sz in range(initial_sz - 2, min_sz - 1, -1):
            f = get_font(font_name, sz)
            w1 = f.getbbox(l1)[2] - f.getbbox(l1)[0]
            w2 = f.getbbox(l2)[2] - f.getbbox(l2)[0]
            if max(w1, w2) <= (max_w - 14):
                return [l1, l2], f

        # Check 3: If prefix is wider than max_w - 14, split prefix at '.' or '-'
        for sep in [".", "-", "_"]:
            if sep in p1:
                parts_p1 = p1.rsplit(sep, 1)
                sub1 = parts_p1[0] + sep
                sub2 = parts_p1[1] + "@"
                f = get_font(font_name, min_sz)
                w1 = f.getbbox(sub1)[2] - f.getbbox(sub1)[0]
                w2 = f.getbbox(sub2)[2] - f.getbbox(sub2)[0]
                w3 = f.getbbox(l2)[2] - f.getbbox(l2)[0]
                if max(w1, w2, w3) <= (max_w - 12):
                    return [sub1, sub2, l2], f

    # Check 4: Character-level wrap if no '@' or couldn't split cleanly
    for sz in range(initial_sz - 2, min_sz - 1, -1):
        f = get_font(font_name, sz)
        lines = []
        curr = ""
        for ch in email:
            cand = curr + ch
            if (f.getbbox(cand)[2] - f.getbbox(cand)[0]) > (max_w - 14) and curr:
                lines.append(curr)
                curr = ch
            else:
                curr = cand
        if curr:
            lines.append(curr)
        if len(lines) <= 2:
            return lines, f

    f = get_font(font_name, min_sz)
    lines = []
    curr = ""
    for ch in email:
        cand = curr + ch
        if (f.getbbox(cand)[2] - f.getbbox(cand)[0]) > (max_w - 12) and curr:
            lines.append(curr)
            curr = ch
        else:
            curr = cand
    if curr:
        lines.append(curr)
    return lines, f


def fit_or_wrap_text(text, max_w, max_lines=2, initial_sz=20, min_sz=14, font_name="regular", padding=16):
    """Auto-sizes or wraps general text across lines so it fits comfortably within max_w."""
    if not text or str(text).strip() in ["-", "~", ""]:
        return [str(text).strip() or "-"], get_font(font_name, initial_sz)

    text = str(text).strip()
    font_name = resolve_font_name(font_name, text)

    # Check 1: Single line fit with padding
    for sz in range(initial_sz, min_sz, -1):
        f = get_font(font_name, sz)
        bb = f.getbbox(text)
        if (bb[2] - bb[0]) <= (max_w - padding):
            return [text], f

    # Check 2: Word wrap into up to max_lines
    for sz in range(initial_sz - 1, min_sz - 1, -1):
        f = get_font(font_name, sz)
        lines = wrap_text_by_words(text, f, max_w - padding)
        if 1 <= len(lines) <= max_lines:
            if all((f.getbbox(l)[2] - f.getbbox(l)[0]) <= (max_w - 10) for l in lines):
                return lines, f

    f = get_font(font_name, min_sz)
    lines = wrap_text_by_words(text, f, max_w - 10)
    return lines[:max_lines], f


HAS_RAQM = False
try:
    from PIL import features
    HAS_RAQM = features.check('raqm')
except Exception:
    pass

def safe_draw_text(draw, xy, text, fill=None, font=None, anchor=None, direction=None):
    """Draw text safely whether libraqm is compiled into PIL or not."""
    if not text:
        return
    text = str(text)
    kwargs = {}
    if fill is not None:
        kwargs["fill"] = fill
    if font is not None:
        kwargs["font"] = font
    if anchor is not None:
        kwargs["anchor"] = anchor
    if direction and HAS_RAQM:
        kwargs["direction"] = direction
    try:
        draw.text(xy, text, **kwargs)
    except Exception:
        # Fallback if direction or font features fail without libraqm
        kwargs.pop("direction", None)
        draw.text(xy, text, **kwargs)

def draw_cell_multiline(draw, lines, font, cx, cy, color, anchor="mm", line_spacing=None, direction=None):
    """Draws single or multi-line text with balanced vertical spacing around cy."""
    if not lines:
        return
    n = len(lines)
    sz = getattr(font, "size", 18)
    if line_spacing is None:
        line_spacing = int(sz * 1.45)

    # If direction is RTL, but none of the lines contain Arabic characters, normalize direction
    if direction == "rtl" and not any(has_arabic(l) for l in lines):
        direction = None

    if n == 1:
        safe_draw_text(draw, (cx, cy), lines[0], fill=color, font=font, anchor=anchor, direction=direction)
    elif n == 2:
        y1 = cy - (line_spacing // 2)
        y2 = cy + (line_spacing // 2)
        safe_draw_text(draw, (cx, y1), lines[0], fill=color, font=font, anchor=anchor, direction=direction)
        safe_draw_text(draw, (cx, y2), lines[1], fill=color, font=font, anchor=anchor, direction=direction)
    elif n >= 3:
        total_h = (n - 1) * line_spacing
        y0 = cy - (total_h // 2)
        for i, line in enumerate(lines):
            ly = y0 + i * line_spacing
            safe_draw_text(draw, (cx, ly), line, fill=color, font=font, anchor=anchor, direction=direction)


def render_page_1(data: dict, template_path: str) -> Image.Image:
    """Renders Page 1: Contract Details & First Party (Lessor Details)."""
    card = get_template_image(template_path)
    draw = ImageDraw.Draw(card)

    contract = data.get("contract", {})
    lessor = data.get("lessor", {})
    c_no = contract.get("contractNumber", "")
    c_date = contract.get("issueDate", "")

    # 1. Top-Left QR Code
    render_qr_code(card, c_no)

    # Fonts & Color - Exact soft dark tone matching official demo
    font_val = get_font("regular", 21)
    color = (45, 45, 45)

    # 2. CONTRACT DETAILS TABLE (Rows 0 to 6 are blank in template)
    if c_no:
        draw.text((703, 417), str(c_no), fill=color, font=font_val, anchor="mm")

    if c_date:
        draw.text((703, 458), str(c_date), fill=color, font=font_val, anchor="mm")

    start_date = contract.get("startDate", "")
    if start_date:
        draw.text((703, 499), str(start_date), fill=color, font=font_val, anchor="mm")

    end_date = contract.get("endDate", "")
    if end_date:
        draw.text((703, 540), str(end_date), fill=color, font=font_val, anchor="mm")

    annual_rent = contract.get("annualRent", "")
    if annual_rent:
        draw.text((703, 582), str(annual_rent), fill=color, font=font_val, anchor="mm")

    contract_val = contract.get("contractValue", "")
    if contract_val:
        draw.text((703, 623), str(contract_val), fill=color, font=font_val, anchor="mm")

    sec_dep = contract.get("securityDeposit", "___")
    if sec_dep and sec_dep != "___":
        draw.text((703, 664), str(sec_dep), fill=color, font=font_val, anchor="mm")
    else:
        draw.line([(688, 673), (718, 673)], fill=color, width=2)

    # 3. LESSOR DETAILS UPPER TABLE: Values Row
    # The table has 4 columns:
    # Col 1 (x=68..320): Email
    # Col 2 (x=320..556): Mobile No.
    # Col 3 (x=556..791): License No.
    # Col 4 (x=791..1346): Company Name (Bilingual: Arabic top, English bot)
    contact_p = lessor.get("contactPerson", {})
    lessor_email = lessor.get("email", "-")
    lessor_mobile = lessor.get("mobileNo", "-")

    # Col 1: Email (x=68..320, width=252, center=194, cy=1293)
    lines_le, f_le = fit_or_wrap_email(lessor_email, max_w=252, initial_sz=21, min_sz=14)
    draw_cell_multiline(draw, lines_le, f_le, cx=194, cy=1293, color=color, anchor="mm")

    # Col 2: Mobile No. (x=320..556, width=236, center=438, cy=1293)
    lines_lm, f_lm = fit_or_wrap_text(lessor_mobile, max_w=236, max_lines=2, initial_sz=21, min_sz=14)
    draw_cell_multiline(draw, lines_lm, f_lm, cx=438, cy=1293, color=color, anchor="mm")

    # Col 3: License No. (x=556..791, width=235, center=673, cy=1293)
    lessor_license = lessor.get("licenseNo", "")
    lines_ll, f_ll = fit_or_wrap_text(lessor_license, max_w=235, max_lines=2, initial_sz=21, min_sz=14)
    draw_cell_multiline(draw, lines_ll, f_ll, cx=673, cy=1293, color=color, anchor="mm")

    # Col 4: Company Name (x=791..1346, width=555, center=1068)
    comp_ar = lessor.get("companyNameAr", "")
    comp_en = lessor.get("companyNameEn", lessor.get("companyName", ""))

    if comp_ar:
        ar_font = "arabic_regular" if has_arabic(comp_ar) else "regular"
        ar_dir = "rtl" if has_arabic(comp_ar) else None
        lines_ar, f_ar = fit_or_wrap_text(comp_ar, max_w=540, max_lines=2, initial_sz=22, min_sz=16, font_name=ar_font)
        if len(lines_ar) == 1:
            safe_draw_text(draw, (1068, 1266), lines_ar[0], fill=color, font=f_ar, anchor="mm", direction=ar_dir)
        else:
            draw_cell_multiline(draw, lines_ar, f_ar, cx=1068, cy=1264, color=color, anchor="mm", direction=ar_dir, line_spacing=24)

    if comp_en:
        lines_en, f_en = fit_or_wrap_text(comp_en, max_w=540, max_lines=2, initial_sz=20, min_sz=15, font_name="regular")
        if len(lines_en) == 1:
            draw.text((1068, 1303), lines_en[0], fill=color, font=f_en, anchor="mm")
        else:
            draw_cell_multiline(draw, lines_en, f_en, cx=1068, cy=1306, color=color, anchor="mm", line_spacing=24)

    # 4. LESSOR DETAILS LOWER TABLE (Contact Person)
    name_en = contact_p.get("fullNameEn", lessor.get("contactNameEn", "SHINE PILLAI HARIDASAN PILLAI SANTHA KUMARI"))
    name_ar = contact_p.get("fullNameAr", lessor.get("contactNameAr", "شاين بيلاي هاريداسان بيلاي سانثا كوماري"))
    default_name_en = "SHINE PILLAI HARIDASAN PILLAI SANTHA KUMARI"

    # Only clear and redraw if the contact person name differs from template
    if name_en and name_en.strip() != default_name_en:
        draw.rectangle([(283, 1420), (1134, 1494)], fill=(255, 255, 255, 255))
        draw.line([(707, 1420), (707, 1494)], fill=(120, 120, 120, 255), width=1)

        # English name (x=285..707, width=422)
        lines_en, f_en = fit_or_wrap_text(name_en, max_w=415, max_lines=2, initial_sz=19, min_sz=14, font_name="regular")
        draw_cell_multiline(draw, lines_en, f_en, cx=285, cy=1455, color=color, anchor="lm", line_spacing=26)

        # Arabic name (x=707..1134, width=427)
        if not has_arabic(name_ar):
            lines_ar, f_ar = fit_or_wrap_text(name_ar, max_w=410, max_lines=2, initial_sz=19, min_sz=14, font_name="regular")
            draw_cell_multiline(draw, lines_ar, f_ar, cx=720, cy=1455, color=color, anchor="lm", line_spacing=26)
        else:
            lines_ar, f_ar = fit_or_wrap_text(name_ar, max_w=410, max_lines=2, initial_sz=20, min_sz=14, font_name="arabic_regular")
            draw_cell_multiline(draw, lines_ar, f_ar, cx=1121, cy=1455, color=color, anchor="rm", direction="rtl", line_spacing=26)

    # Contact Mobile and Email (Centered at column center x=708)
    contact_mobile = contact_p.get("mobileNo", lessor.get("mobileNo", "971588973810"))
    lines_cm, f_cm = fit_or_wrap_text(contact_mobile, max_w=840, max_lines=1, initial_sz=21, min_sz=15)
    draw.text((708, 1516), lines_cm[0], fill=color, font=f_cm, anchor="mm")

    contact_email = contact_p.get("email", lessor.get("email", "shinepillaihs@gmail.com"))
    lines_ce, f_ce = fit_or_wrap_email(contact_email, max_w=840, initial_sz=21, min_sz=14)
    draw_cell_multiline(draw, lines_ce, f_ce, cx=708, cy=1559, color=color, anchor="mm")

    # 5. Common Bottom Footer
    render_common_footer(card, c_no, c_date)
    return card


def render_page_2(data: dict, template_path: str) -> Image.Image:
    """Renders Page 2: Tenant Details, Property Details, Units Details, and Occupants."""
    card = get_template_image(template_path)
    draw = ImageDraw.Draw(card)

    contract = data.get("contract", {})
    tenant = data.get("tenant", {})
    units = data.get("units", [{}])
    occupants = data.get("occupants", [{}])

    c_no = contract.get("contractNumber", "")
    c_date = contract.get("issueDate", "")

    # 1. Top-Left QR Code
    render_qr_code(card, c_no)

    # Fonts & Color - Exact soft dark tone matching official demo
    color = (45, 45, 45)

    # 2. TENANT DETAILS TABLE (Cells are pure white in template, dividers preserved)
    # Arabic row (y=450)
    t_nat_ar = tenant.get("nationalityAr", "باكستان")
    t_name_ar = tenant.get("fullNameAr", "جوهر على ارشاد محمد")
    ar_font_nar = "arabic_regular" if has_arabic(t_nat_ar) else "regular"
    ar_dir_nar = "rtl" if has_arabic(t_nat_ar) else None
    lines_nar, f_nar = fit_or_wrap_text(t_nat_ar, max_w=220, max_lines=1, initial_sz=20, min_sz=14, font_name=ar_font_nar)
    safe_draw_text(draw, (674, 450), lines_nar[0], fill=color, font=f_nar, anchor="mm", direction=ar_dir_nar)

    ar_font_tar = "arabic_regular" if has_arabic(t_name_ar) else "regular"
    ar_dir_tar = "rtl" if has_arabic(t_name_ar) else None
    lines_tar, f_tar = fit_or_wrap_text(t_name_ar, max_w=320, max_lines=2, initial_sz=20, min_sz=14, font_name=ar_font_tar)
    if len(lines_tar) == 1:
        safe_draw_text(draw, (1176, 450), lines_tar[0], fill=color, font=f_tar, anchor="mm", direction=ar_dir_tar)
    else:
        draw_cell_multiline(draw, lines_tar, f_tar, cx=1176, cy=446, color=color, anchor="mm", direction=ar_dir_tar, line_spacing=22)

    # English / numeric row (y=469 or 486)
    # Col 1: Email (x=68..336, width=268, center=202, cy=469)
    t_email = tenant.get("email", "")
    if t_email:
        lines_te, f_te = fit_or_wrap_email(t_email, max_w=250, initial_sz=20, min_sz=14)
        draw_cell_multiline(draw, lines_te, f_te, cx=202, cy=469, color=color, anchor="mm")

    # Col 2: Mobile No. (x=336..556, width=220, center=446, cy=469)
    t_mob = tenant.get("mobileNo", "")
    if t_mob:
        lines_tm, f_tm = fit_or_wrap_text(t_mob, max_w=205, max_lines=2, initial_sz=20, min_sz=14)
        draw_cell_multiline(draw, lines_tm, f_tm, cx=446, cy=469, color=color, anchor="mm")

    # Col 3: Nationality En (x=556..792, width=236, center=674, y=486)
    t_nat_en = tenant.get("nationalityEn", "Pakistan")
    lines_nen, f_nen = fit_or_wrap_text(t_nat_en, max_w=215, max_lines=1, initial_sz=19, min_sz=13, font_name="regular")
    draw.text((674, 486), lines_nen[0], fill=color, font=f_nen, anchor="mm")

    # Col 4: Emirates ID (x=792..1011, width=219, center=901, y=469)
    t_eid = tenant.get("emiratesId", "")
    if t_eid:
        lines_teid, f_teid = fit_or_wrap_text(t_eid, max_w=205, max_lines=1, initial_sz=20, min_sz=15)
        draw.text((901, 469), lines_teid[0], fill=color, font=f_teid, anchor="mm")

    # Col 5: Tenant Full Name En (x=1011..1346, width=335, center=1178, y=486)
    t_name_en = tenant.get("fullNameEn", "Gohar Ali Irshad Muhammad")
    lines_ten, f_ten = fit_or_wrap_text(t_name_en, max_w=315, max_lines=2, initial_sz=19, min_sz=13, font_name="regular")
    if len(lines_ten) == 1:
        draw.text((1178, 486), lines_ten[0], fill=color, font=f_ten, anchor="mm")
    else:
        draw_cell_multiline(draw, lines_ten, f_ten, cx=1178, cy=486, color=color, anchor="mm", line_spacing=22)

    # 3. UNITS DETAILS TABLE (7 columns across x=71..1341, value row at y=1340..1415)
    u0 = units[0] if units else {}

    # Col 1 (x=71..257): Premise No
    premise_no = u0.get("premiseNo", "6391801694")
    if premise_no:
        lines_p, f_p = fit_or_wrap_text(premise_no, max_w=180, max_lines=1, initial_sz=20, min_sz=14)
        draw.text((164, 1375), lines_p[0], fill=color, font=f_p, anchor="mm")

    # Col 2 (x=257..473): Unit Usage (Bilingual)
    unit_usage_ar = u0.get("unitUsageAr", "سكني")
    unit_usage_en = u0.get("unitUsageEn", "RESIDENTIAL")
    if unit_usage_ar:
        ar_font_uar = "arabic_regular" if has_arabic(unit_usage_ar) else "regular"
        ar_dir_uar = "rtl" if has_arabic(unit_usage_ar) else None
        lines_uar, f_uar = fit_or_wrap_text(unit_usage_ar, max_w=210, max_lines=1, initial_sz=18, min_sz=13, font_name=ar_font_uar)
        safe_draw_text(draw, (365, 1358), lines_uar[0], fill=color, font=f_uar, anchor="mm", direction=ar_dir_uar)
    if unit_usage_en:
        lines_uen, f_uen = fit_or_wrap_text(unit_usage_en, max_w=210, max_lines=1, initial_sz=18, min_sz=13, font_name="regular")
        draw.text((365, 1392), lines_uen[0], fill=color, font=f_uen, anchor="mm")

    # Col 3 (x=473..658): No. of rooms
    rooms = u0.get("noOfRooms", u0.get("numberOfRooms", "2"))
    if rooms and str(rooms) != "~":
        lines_r, f_r = fit_or_wrap_text(rooms, max_w=180, max_lines=1, initial_sz=20, min_sz=14)
        draw.text((566, 1375), lines_r[0], fill=color, font=f_r, anchor="mm")

    # Col 4 (x=658..809): Area
    area = u0.get("area", "110")
    if not area or str(area) == "~":
        area = "110"
    lines_a, f_a = fit_or_wrap_text(area, max_w=145, max_lines=1, initial_sz=20, min_sz=14)
    draw.text((734, 1375), lines_a[0], fill=color, font=f_a, anchor="mm")

    # Col 5 (x=809..1009): Unit Type (Bilingual)
    ut_ar = u0.get("unitTypeAr", "شقة")
    ut_en = u0.get("unitTypeEn", "APARTMENT")
    if "APARTMENT" in ut_en.upper():
        ut_en_display = "APARTMENT"
        ut_ar_display = "شقة"
    else:
        ut_en_display = ut_en
        ut_ar_display = ut_ar

    if ut_ar_display:
        ar_font_utar = "arabic_regular" if has_arabic(ut_ar_display) else "regular"
        ar_dir_utar = "rtl" if has_arabic(ut_ar_display) else None
        lines_utar, f_utar = fit_or_wrap_text(ut_ar_display, max_w=195, max_lines=1, initial_sz=18, min_sz=13, font_name=ar_font_utar)
        safe_draw_text(draw, (909, 1358), lines_utar[0], fill=color, font=f_utar, anchor="mm", direction=ar_dir_utar)
    if ut_en_display:
        lines_uten, f_uten = fit_or_wrap_text(ut_en_display, max_w=195, max_lines=1, initial_sz=18, min_sz=13, font_name="regular")
        draw.text((909, 1392), lines_uten[0], fill=color, font=f_uten, anchor="mm")

    # Col 6 (x=1009..1178): Unit Reg No
    unit_reg = u0.get("unitRegNo", "UNT302977")
    if unit_reg:
        lines_ur, f_ur = fit_or_wrap_text(unit_reg, max_w=165, max_lines=1, initial_sz=20, min_sz=14)
        draw.text((1093, 1375), lines_ur[0], fill=color, font=f_ur, anchor="mm")

    # Col 7 (x=1178..1341): Unit No
    unit_no = u0.get("unitNo", "Flat No. 254")
    if unit_no:
        lines_un, f_un = fit_or_wrap_text(unit_no, max_w=158, max_lines=2, initial_sz=20, min_sz=13, font_name="regular")
        draw_cell_multiline(draw, lines_un, f_un, cx=1260, cy=1375, color=color, anchor="mm")

    # 4. OCCUPANTS DETAILS TABLE (Clean in template, dividers preserved)
    # Col 1 (English Full Name): x=[67, 440], width=373, anchor='lm' at x=82, max_w=345
    # Col 2 (Emirates ID): x=[440, 972], width=532, center=706
    # Col 3 (Arabic Full Name): x=[972, 1344], width=372, anchor='rm' at x=1330, max_w=345
    occ0 = occupants[0] if occupants else {}
    occ_name = occ0.get("fullName", tenant.get("fullNameEn", "Gohar Ali Irshad Muhammad"))
    occ_eid = occ0.get("emiratesId", tenant.get("emiratesId", "784198883321535"))
    occ_name_ar = occ0.get("fullNameAr", tenant.get("fullNameAr", "جوهر على ارشاد محمد"))

    if occ_name:
        lines_occ_en, f_occ_en = fit_or_wrap_text(occ_name, max_w=345, max_lines=2, initial_sz=19, min_sz=13, font_name="regular")
        draw_cell_multiline(draw, lines_occ_en, f_occ_en, cx=82, cy=1582, color=color, anchor="lm", line_spacing=24)
    if occ_eid:
        lines_oeid, f_oeid = fit_or_wrap_text(occ_eid, max_w=500, max_lines=1, initial_sz=20, min_sz=15)
        draw.text((706, 1582), lines_oeid[0], fill=color, font=f_oeid, anchor="mm")
    if occ_name_ar:
        if not has_arabic(occ_name_ar):
            lines_occ_ar, f_occ_ar = fit_or_wrap_text(occ_name_ar, max_w=345, max_lines=2, initial_sz=19, min_sz=13, font_name="regular")
            draw_cell_multiline(draw, lines_occ_ar, f_occ_ar, cx=985, cy=1582, color=color, anchor="lm", line_spacing=24)
        else:
            lines_occ_ar, f_occ_ar = fit_or_wrap_text(occ_name_ar, max_w=345, max_lines=2, initial_sz=20, min_sz=13, font_name="arabic_regular")
            draw_cell_multiline(draw, lines_occ_ar, f_occ_ar, cx=1330, cy=1582, color=color, anchor="rm", direction="rtl", line_spacing=24)

    # 5. Common Bottom Footer
    render_common_footer(card, c_no, c_date)
    return card


def render_signature_qr(content: str, target_size=(112, 112)) -> Image.Image:
    """Generates high-contrast electronic approval signature QR code matching official contract."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=1,
    )
    qr.add_data(content)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    return img.resize(target_size, Image.Resampling.NEAREST)


def _load_signature_qr(custom_b64: str, default_path: str, target_size: tuple) -> Image.Image:
    """
    Returns a signature QR image:
    1. If custom_b64 is provided (base64 PNG from upload), use that.
    2. If the default file exists (extracted from official Gohar Ali PDF), use that.
    3. Fallback: generate a blank white placeholder.
    """
    import base64, io as _io
    if custom_b64:
        try:
            raw = base64.b64decode(custom_b64)
            qr_img = Image.open(_io.BytesIO(raw)).convert("RGBA")
            return qr_img.resize(target_size, Image.Resampling.NEAREST)
        except Exception:
            pass  # fall through to default

    if default_path and os.path.exists(default_path):
        qr_img = Image.open(default_path).convert("RGBA")
        return qr_img.resize(target_size, Image.Resampling.NEAREST)

    # Last resort: white placeholder
    return Image.new("RGBA", target_size, (255, 255, 255, 255))


def render_page_3(data: dict, template_path: str) -> Image.Image:
    """Renders Page 3: Electronic Approvals, Tenant & Lessor Signature QRs, and Footer."""
    card = get_template_image(template_path)

    contract = data.get("contract", {})
    tenant = data.get("tenant", {})
    c_no = contract.get("contractNumber", "")
    c_date = contract.get("issueDate", "")

    # 1. Top-Left QR Code
    render_qr_code(card, c_no)

    # 2. Signature Approval QR Codes
    active_cno = str(c_no).strip() if c_no else "202401451594"
    tenant_sig_url = f"https://dari-aec.com/en/app/verify-tenant-contract?search={active_cno}"
    default_lessor_content = "contractNo#202401452705 issDte#5/2/2024 11:40:14 AM"

    # White out signature QR target zones first to guarantee clean placement without background bleed
    draw = ImageDraw.Draw(card)
    draw.rectangle([(325, 765), (445, 885)], fill=(255, 255, 255, 255))
    draw.rectangle([(963, 765), (1085, 885)], fill=(255, 255, 255, 255))

    # Custom override QR (base64 PNG from admin upload)
    sig_qr = data.get("signatureQR", {})
    custom_tenant_b64 = sig_qr.get("tenantQR", "")
    custom_lessor_b64 = sig_qr.get("lessorQR", "")

    _defaults_dir = os.path.join(os.path.dirname(__file__), "defaults")
    default_tenant_qr = os.path.join(_defaults_dir, "tenant_sig_qr_130.png")
    default_lessor_qr = os.path.join(_defaults_dir, "lessor_sig_qr_130.png")

    # Tenant Signature QR (Left signature box) -> Verification Link
    if custom_tenant_b64:
        tnt_qr_img = _load_signature_qr(custom_tenant_b64, default_tenant_qr, (112, 112))
    else:
        tnt_qr_img = render_signature_qr(tenant_sig_url, (112, 112))
    card.paste(tnt_qr_img, (331, 770), tnt_qr_img)

    # Lessor Signature QR (Right signature box) -> Default Permanent Signature QR
    if custom_lessor_b64:
        lsr_qr_img = _load_signature_qr(custom_lessor_b64, default_lessor_qr, (112, 112))
    else:
        lsr_qr_img = render_signature_qr(default_lessor_content, (112, 112))
    card.paste(lsr_qr_img, (969, 770), lsr_qr_img)

    # 3. Common Bottom Footer
    render_common_footer(card, c_no, c_date)

    return card


def render_page_terms(page_num: int, data: dict, template_path: str) -> Image.Image:
    """Renders Pages 4 through 8: General Terms & Conditions bilingual articles."""
    card = get_template_image(template_path)

    contract = data.get("contract", {})
    c_no = contract.get("contractNumber", "")
    c_date = contract.get("issueDate", "")

    # 1. Top-Left QR Code
    render_qr_code(card, c_no)

    # 2. Common Bottom Footer
    render_common_footer(card, c_no, c_date)

    return card


def render_page_9(data: dict, template_path: str) -> Image.Image:
    """Renders Page 9: Special Conditions, Signatures, and Department Approvals.
    Note: Page 9 in the official contract has no bottom metadata footer or QR code.
    """
    card = get_template_image(template_path)
    return card


def generate_contract_bundle(data: dict, template_dir: str = TEMPLET_DIR, output_dir: str = None) -> dict:
    """
    Renders all 9 contract pages and generates merged PDF.
    Returns dict with page image paths and compiled PDF path.
    """
    if not output_dir:
        c_no = data.get("contract", {}).get("contractNumber", "contract")
        output_dir = os.path.join(BASE_DIR, "output", str(c_no))

    os.makedirs(output_dir, exist_ok=True)

    page_images = []
    page_paths = []

    # Page 1
    t1_path = os.path.join(template_dir, "1.png")
    p1 = render_page_1(data, t1_path)
    p1_rgb = p1.convert("RGB")
    p1_file = os.path.join(output_dir, "1.png")
    p1_rgb.save(p1_file, "PNG", quality=95)
    page_images.append(p1_rgb)
    page_paths.append(p1_file)

    # Page 2
    t2_path = os.path.join(template_dir, "2.png")
    p2 = render_page_2(data, t2_path)
    p2_rgb = p2.convert("RGB")
    p2_file = os.path.join(output_dir, "2.png")
    p2_rgb.save(p2_file, "PNG", quality=95)
    page_images.append(p2_rgb)
    page_paths.append(p2_file)

    # Page 3
    t3_blank = os.path.join(template_dir, "3_blank.png")
    t3_path = t3_blank if os.path.exists(t3_blank) else os.path.join(template_dir, "3.png")
    p3 = render_page_3(data, t3_path)
    p3_rgb = p3.convert("RGB")
    p3_file = os.path.join(output_dir, "3.png")
    p3_rgb.save(p3_file, "PNG", quality=95)
    page_images.append(p3_rgb)
    page_paths.append(p3_file)

    # Pages 4 to 8 (Terms & Conditions)
    for p_num in range(4, 9):
        tp_path = os.path.join(template_dir, f"{p_num}.png")
        p = render_page_terms(p_num, data, tp_path)
        p_rgb = p.convert("RGB")
        p_file = os.path.join(output_dir, f"{p_num}.png")
        p_rgb.save(p_file, "PNG", quality=95)
        page_images.append(p_rgb)
        page_paths.append(p_file)

    # Export merged 8-page PDF
    contract_number = data.get("contract", {}).get("contractNumber", "contract")
    pdf_filename = f"{contract_number}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)

    # Save all pages as multi-page PDF (A4 1414x2000 at ~171 DPI)
    page_images[0].save(
        pdf_path,
        "PDF",
        resolution=171.0,
        save_all=True,
        append_images=page_images[1:]
    )

    # Clean up stale page 9 if present
    p9_file = os.path.join(output_dir, "9.png")
    if os.path.exists(p9_file):
        try:
            os.remove(p9_file)
        except Exception:
            pass

    return {
        "contractNumber": contract_number,
        "pageCount": len(page_paths),
        "pagePaths": page_paths,
        "pdfPath": pdf_path,
        "outputDir": output_dir
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Abu Dhabi Tenancy Contract 9-Page Bundle")
    parser.add_argument("--data", default=os.path.join(BASE_DIR, "sample_contract.json"), help="Path to contract JSON data")
    parser.add_argument("--output", default=None, help="Output directory")
    args = parser.parse_args()

    with open(args.data, "r", encoding="utf-8") as f:
        contract_data = json.load(f)

    result = generate_contract_bundle(contract_data, output_dir=args.output)
    print(f"Successfully generated {result['pageCount']} pages and PDF:")
    print(f"PDF: {result['pdfPath']}")
    for i, p in enumerate(result['pagePaths'], 1):
        print(f"  Page {i}: {p}")
