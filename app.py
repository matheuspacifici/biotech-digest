import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime

# SendGrid — only imported if API key is configured
def send_digest_email(to_email: str, subject: str, html_body: str) -> tuple[bool, str]:
    """Send HTML email via SendGrid. Returns (success, message)."""
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Email, To, Content
    except ImportError:
        return False, "sendgrid library not installed"

    api_key = st.secrets.get("SENDGRID_API_KEY", os.environ.get("SENDGRID_API_KEY", ""))
    from_email = st.secrets.get("SENDGRID_FROM_EMAIL", os.environ.get("SENDGRID_FROM_EMAIL", ""))

    if not api_key or not from_email:
        return False, "SendGrid not configured — add SENDGRID_API_KEY and SENDGRID_FROM_EMAIL to Streamlit secrets"

    try:
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        message = Mail(
            from_email=Email(from_email, "Biotech VC Digest"),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_body)
        )
        response = sg.client.mail.send.post(request_body=message.get())
        if response.status_code in (200, 202):
            return True, f"Digest sent to {to_email}"
        else:
            return False, f"SendGrid error: status {response.status_code}"
    except Exception as e:
        return False, f"Send failed: {str(e)}"


def build_email_html(deals: list, date_str: str) -> str:
    """Build a clean HTML email version of the digest."""
    total_capital = sum(d["deal_size_raw"] for d in deals)
    onc_count = sum(1 for d in deals if d["is_onc"])
    total_fmt = f"${total_capital:.1f}M" if total_capital < 1000 else f"${total_capital/1000:.1f}B"

    def epill(text, bg, fg):
        return f'<span style="font-size:11px;padding:2px 7px;border-radius:20px;background:{bg};color:{fg};margin-right:4px;">{text}</span>'

    def deal_epills(d):
        t = ""
        if d["is_onc"]:   t += epill("Oncology", "#FCEBEB", "#791F1F")
        if d["is_accel"]: t += epill(f"Accelerator ({d['accel_name']})" if d["accel_name"] else "Accelerator", "#E1F5EE", "#085041")
        else:             t += epill("Angel", "#EEEDFE", "#3C3289")
        if d["geo"]:      t += epill(d["geo"], "#F1F5F9", "#475569")
        if d["biz_status"]: t += epill(d["biz_status"], "#E6F1FB", "#0C447C")
        return t

    leaderboard = ""
    for i, d in enumerate(deals, 1):
        synopsis = (d["synopsis"][:220] + "…") if len(d["synopsis"]) > 220 else d["synopsis"]
        leaderboard += f"""
        <tr><td style="padding:12px 0;border-bottom:1px solid #eee;vertical-align:top;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
              <span style="font-size:12px;color:#94A3B8;margin-right:6px;">{i}</span>
              <span style="font-weight:600;font-size:14px;color:#0D1B2A;">{d['company']}</span>
              <div style="margin-top:5px;">{deal_epills(d)}</div>
            </div>
            <div style="font-weight:600;font-size:14px;color:#0D1B2A;white-space:nowrap;padding-left:12px;">{d['deal_size']}</div>
          </div>
          <div style="font-size:12px;color:#475569;line-height:1.6;margin-top:6px;">{synopsis}</div>
        </td></tr>"""

    onc_cards = ""
    for d in [x for x in deals if x["is_onc"]]:
        full = (d["synopsis"][:400] + "…") if len(d["synopsis"]) > 400 else d["synopsis"]
        onc_cards += f"""
        <div style="border:1px solid #FECACA;border-left:4px solid #DC2626;border-radius:8px;padding:14px;margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
            <span style="font-weight:600;font-size:14px;color:#0D1B2A;">{d['company']}</span>
            <span style="font-size:12px;color:#64748B;">{'Accelerator' if d['is_accel'] else 'Angel'} · {d['geo']}</span>
          </div>
          <div style="margin-bottom:7px;">
            {epill('Oncology','#FCEBEB','#791F1F')}
            {epill(d['modality'],'#E6F1FB','#0C447C')}
          </div>
          <div style="font-size:12px;color:#475569;line-height:1.6;">{full}</div>
        </div>"""

    mod_counts = {}
    for d in deals:
        mod_counts[d["modality"]] = mod_counts.get(d["modality"], 0) + 1
    mod_rows = ""
    for m, c in sorted(mod_counts.items(), key=lambda x: -x[1]):
        pct = round(c / len(deals) * 100)
        mod_rows += f'<tr><td style="padding:6px 8px;font-size:12px;border-bottom:1px solid #eee;">{m}</td><td style="padding:6px 8px;text-align:right;font-size:12px;border-bottom:1px solid #eee;">{c}</td><td style="padding:6px 8px;border-bottom:1px solid #eee;"><div style="background:#534AB7;height:6px;border-radius:3px;width:{pct*1.2}px;display:inline-block;"></div> <span style="font-size:10px;color:#94A3B8;">{pct}%</span></td></tr>'

    return f"""<!DOCTYPE html><html><body>
<div style="font-family:system-ui,sans-serif;max-width:640px;margin:0 auto;color:#111;">
  <div style="padding:24px 0 16px;border-bottom:2px solid #0D1B2A;">
    <div style="font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#666;margin-bottom:4px;">Bi-weekly digest · PitchBook</div>
    <h1 style="font-size:22px;font-weight:700;margin:0;color:#0D1B2A;">Biotech Early-Stage Funding</h1>
    <div style="font-size:13px;color:#666;margin-top:4px;">{date_str} · {len(deals)} deals · Angel + Accelerator · Oncology focus</div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:20px 0;">
    <div style="background:#f5f5f3;border-radius:8px;padding:12px;"><div style="font-size:10px;color:#666;margin-bottom:3px;">Total capital</div><div style="font-size:20px;font-weight:700;">{total_fmt}</div></div>
    <div style="background:#f5f5f3;border-radius:8px;padding:12px;"><div style="font-size:10px;color:#666;margin-bottom:3px;">Total deals</div><div style="font-size:20px;font-weight:700;">{len(deals)}</div></div>
    <div style="background:#FCEBEB;border-radius:8px;padding:12px;"><div style="font-size:10px;color:#791F1F;margin-bottom:3px;">Oncology</div><div style="font-size:20px;font-weight:700;color:#791F1F;">{onc_count}</div></div>
  </div>
  <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#94A3B8;margin-bottom:8px;">Deal leaderboard</div>
  <table style="width:100%;border-collapse:collapse;">{leaderboard}</table>
  <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#791F1F;margin:20px 0 8px;">Oncology spotlight</div>
  {onc_cards if onc_cards else '<p style="font-size:13px;color:#888;">No oncology-tagged deals in this batch.</p>'}
  <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#534AB7;margin:20px 0 8px;">Platform modality</div>
  <table style="width:100%;border-collapse:collapse;font-size:12px;">
    <tr style="background:#f5f5f3;"><td style="padding:6px 8px;font-weight:600;">Modality</td><td style="padding:6px 8px;font-weight:600;text-align:right;">Deals</td><td style="padding:6px 8px;font-weight:600;">Share</td></tr>
    {mod_rows}
  </table>
  <div style="margin-top:28px;padding-top:14px;border-top:1px solid #eee;font-size:10px;color:#94A3B8;">
    Compiled by Biotech Early-Stage Digest · Powered by Claude · Source: PitchBook · {date_str}
  </div>
</div></body></html>"""

# ─── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Biotech Early-Stage Funding Digest",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── CUSTOM CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .main { background: #FAFAF9; }
  .block-container { padding: 2rem 3rem; max-width: 1100px; }

  .hero { background: #0D1B2A; border-radius: 12px; padding: 2.5rem 3rem; margin-bottom: 2rem; }
  .hero h1 { color: white; font-size: 2rem; font-weight: 700; margin: 0 0 0.3rem; }
  .hero p { color: #8FB3C8; font-size: 1rem; margin: 0; }
  .hero .sub { color: #0F7173; font-weight: 600; }

  .stat-box { background: white; border: 1px solid #E2E8F0; border-radius: 10px; padding: 1.2rem 1.4rem; }
  .stat-label { font-size: 11px; color: #64748B; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
  .stat-value { font-size: 1.8rem; font-weight: 700; color: #0D1B2A; line-height: 1; }
  .stat-sub { font-size: 11px; color: #94A3B8; margin-top: 3px; }

  .section-title { font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #64748B; margin: 2rem 0 0.8rem; }
  .section-title.onc { color: #791F1F; }
  .section-title.mod { color: #534AB7; }
  .section-title.ta  { color: #0F6E56; }

  .deal-card { background: white; border: 1px solid #E2E8F0; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.7rem; }
  .deal-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; }
  .deal-name { font-size: 15px; font-weight: 600; color: #0D1B2A; }
  .deal-amount { font-size: 15px; font-weight: 600; color: #0D1B2A; white-space: nowrap; }
  .deal-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 7px; }
  .deal-desc { font-size: 13px; color: #475569; line-height: 1.6; }

  .tag { font-size: 11px; padding: 2px 9px; border-radius: 20px; font-weight: 500; }
  .tag-onc  { background: #FCEBEB; color: #791F1F; }
  .tag-angel { background: #EEEDFE; color: #3C3489; }
  .tag-accel { background: #E1F5EE; color: #085041; }
  .tag-geo  { background: #F1F5F9; color: #475569; }
  .tag-stage { background: #E6F1FB; color: #0C447C; }

  .onc-card { background: white; border: 1px solid #FECACA; border-left: 4px solid #DC2626; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.8rem; }
  .onc-name { font-size: 15px; font-weight: 600; color: #0D1B2A; }
  .onc-meta { font-size: 12px; color: #64748B; }

  .rank { font-size: 12px; color: #94A3B8; font-weight: 500; margin-right: 8px; }

  .bar-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; border-bottom: 1px solid #F1F5F9; }
  .bar-label { font-size: 13px; color: #334155; width: 220px; flex-shrink: 0; }
  .bar-track { flex: 1; background: #F1F5F9; border-radius: 4px; height: 8px; }
  .bar-fill-mod { background: #534AB7; border-radius: 4px; height: 8px; }
  .bar-fill-ta  { background: #0F7173; border-radius: 4px; height: 8px; }
  .bar-count { font-size: 12px; color: #94A3B8; width: 24px; text-align: right; }

  .upload-zone { background: white; border: 2px dashed #CBD5E1; border-radius: 12px; padding: 3rem 2rem; text-align: center; margin-bottom: 2rem; }
  .upload-zone h3 { color: #0D1B2A; font-size: 1.1rem; margin-bottom: 0.5rem; }
  .upload-zone p { color: #64748B; font-size: 0.9rem; }

  .footer { margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid #E2E8F0; font-size: 11px; color: #94A3B8; text-align: center; }

  /* Hide streamlit branding */
  #MainMenu { visibility: hidden; }
  footer { visibility: hidden; }
  header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─── CLASSIFICATION LOGIC ──────────────────────────────────────────────────────

def extract_modality(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["sirna", "oligonucleotide", "rnai", "antisense", "mrna therapeutic"]):
        return "RNA therapeutics"
    if "mrna vaccine" in t or ("mrna" in t and "vaccine" in t):
        return "mRNA vaccine"
    if any(k in t for k in ["protac", "molecular glue", "degrader", "proximity"]):
        return "Targeted protein degradation"
    if any(k in t for k in ["car-t", "cart", "car t", "t cell engager", "bispecific"]):
        return "Cell therapy / bispecific"
    if any(k in t for k in ["natural killer", "nk cell", "nk therapy"]):
        return "Cell therapy (NK)"
    if any(k in t for k in ["bacteriophage", "phage"]):
        return "Bacteriophage"
    if any(k in t for k in ["small molecule", "oral", "inhibitor", "kinase"]):
        return "Small molecule"
    if any(k in t for k in ["gene therapy", "gene editing", "crispr", "aav", "viral vector"]):
        return "Gene therapy / editing"
    if any(k in t for k in ["ai", "machine learning", "deep learning", "computational"]):
        return "AI drug discovery"
    if any(k in t for k in ["hyaluronic", "biomolecule", "biopolymer"]):
        return "Biomolecule / HA"
    if any(k in t for k in ["cultivated meat", "cell line", "agtech", "animal cell"]):
        return "Cultivated meat / AgTech"
    if any(k in t for k in ["antibody", "monoclonal", "biologic"]):
        return "Biologic / antibody"
    return "Other / platform"

def extract_ta(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["oncology", "cancer", "tumor", "leukemia", "lymphoma", "myeloma"]):
        return "Oncology"
    if any(k in t for k in ["autoimmune", "inflammatory", "immune"]):
        return "Autoimmune / immunology"
    if any(k in t for k in ["cardiovascular", "cardiac", "heart"]):
        return "Cardiovascular"
    if any(k in t for k in ["neurolog", "neurodegenerative", "cns", "brain"]):
        return "Neurology / CNS"
    if any(k in t for k in ["rare disease", "orphan", "genetic disorder"]):
        return "Rare disease"
    if any(k in t for k in ["infectious", "antimicrobial", "antibiotic", "bacteriophage", "pathogen"]):
        return "Infectious disease"
    if any(k in t for k in ["renal", "kidney", "dialysis"]):
        return "Renal"
    if any(k in t for k in ["aquaculture", "animal health", "cultivated meat", "agtech", "livestock"]):
        return "Animal health / AgTech"
    if any(k in t for k in ["cosmetic", "aesthetic", "dermal", "skin"]):
        return "Aesthetics / dermatology"
    return "Other"

def format_amount(size: float, currency: str) -> str:
    if size == 0:
        return "Undisclosed"
    if "EUR" in currency or "Euro" in currency:
        symbol = "€"
    elif "CHF" in currency or "Swiss" in currency:
        symbol = "CHF "
    elif "GBP" in currency or "British" in currency:
        symbol = "£"
    else:
        symbol = "$"
    if size >= 1000:
        return f"{symbol}{size/1000:.1f}B"
    elif size >= 1:
        return f"{symbol}{size:.1f}M"
    else:
        return f"{symbol}{size*1000:.0f}K"

def parse_pitchbook(file) -> list:
    raw = pd.read_excel(file, header=None)
    header_row = None
    for i, row in raw.iterrows():
        if "Deal ID" in str(list(row.values)):
            header_row = i
            break
    if header_row is None:
        st.error("Could not find 'Deal ID' column. Please upload a PitchBook 'All Columns' export.")
        return []

    df = pd.read_excel(file, header=header_row)
    df = df[df["Deal ID"].notna() & ~df["Deal ID"].astype(str).str.startswith("©")]

    deals = []
    seen = set()

    for _, row in df.iterrows():
        company = str(row.get("Companies", "")).strip()
        if not company or company == "nan":
            continue

        try:
            deal_size = float(row.get("Deal Size", 0)) if pd.notna(row.get("Deal Size", 0)) else 0.0
        except:
            deal_size = 0.0

        if company in seen:
            for d in deals:
                if d["company"] == company and deal_size > d["deal_size_raw"]:
                    d["deal_size_raw"] = deal_size
                    currency = str(row.get("Native Currency of Deal", "US Dollars (USD)"))
                    d["deal_size"] = format_amount(deal_size, currency)
            continue
        seen.add(company)

        deal_type = str(row.get("Deal Type", "")).strip()
        is_accel = "accelerator" in deal_type.lower() or "incubator" in deal_type.lower()
        verticals = str(row.get("Verticals", "")).lower()
        keywords  = str(row.get("Keywords", "")).lower()
        desc      = str(row.get("Description", "")).lower()
        synopsis  = str(row.get("Deal Synopsis", row.get("Financing Status Note", ""))).strip()
        is_onc    = "oncology" in verticals or "oncology" in keywords or "cancer" in keywords

        country = str(row.get("Company Country/Territory/Region", "")).strip()
        city    = str(row.get("Company City", "")).strip()
        state   = str(row.get("Company State/Province", "")).strip()
        if country == "United States" and city:
            geo = f"{city}{', ' + state if state else ''}"
        elif country and country != "nan":
            geo = country
        else:
            geo = "—"

        deal_date = row.get("Deal Date", row.get("Announced Date", ""))
        if pd.notna(deal_date):
            try:
                deal_date = pd.to_datetime(deal_date).strftime("%b %d, %Y")
            except:
                deal_date = str(deal_date)[:10]
        else:
            deal_date = ""

        investors_raw = str(row.get("Investors", "")).strip()
        accel_name = investors_raw.split("(")[0].strip() if is_accel and investors_raw != "nan" else ""

        currency = str(row.get("Native Currency of Deal", "US Dollars (USD)"))
        biz_status = str(row.get("Current Business Status", row.get("Business Status", ""))).strip()
        biz_status = "" if biz_status == "nan" else biz_status

        deals.append({
            "company":       company,
            "deal_size":     format_amount(deal_size, currency),
            "deal_size_raw": deal_size,
            "deal_type":     deal_type,
            "is_accel":      is_accel,
            "accel_name":    accel_name,
            "is_onc":        is_onc,
            "geo":           geo,
            "biz_status":    biz_status,
            "synopsis":      synopsis if synopsis != "nan" else "",
            "description":   str(row.get("Description", "")).strip(),
            "deal_date":     deal_date,
            "modality":      extract_modality(str(row.get("Description",""))+" "+str(row.get("Keywords",""))),
            "ta":            extract_ta(verticals+" "+keywords+" "+desc),
        })

    deals.sort(key=lambda x: x["deal_size_raw"], reverse=True)
    return deals[:10]

# ─── TAG HTML HELPER ───────────────────────────────────────────────────────────

def tag(text, cls):
    return f'<span class="tag {cls}">{text}</span>'

def deal_tags(d):
    t = ""
    if d["is_onc"]:
        t += tag("Oncology", "tag-onc")
    if d["is_accel"]:
        label = f"Accelerator ({d['accel_name']})" if d["accel_name"] else "Accelerator"
        t += tag(label, "tag-accel")
    else:
        t += tag("Angel", "tag-angel")
    if d["geo"]:
        t += tag(d["geo"], "tag-geo")
    if d["biz_status"] and d["biz_status"] not in ["nan", "—", ""]:
        t += tag(d["biz_status"], "tag-stage")
    return t

# ─── BAR CHART HTML ────────────────────────────────────────────────────────────

def bar_chart(counts: dict, fill_class: str) -> str:
    if not counts:
        return ""
    max_v = max(counts.values())
    html = ""
    for label, count in sorted(counts.items(), key=lambda x: -x[1]):
        pct = int(count / max_v * 100)
        html += f"""
        <div class="bar-row">
          <div class="bar-label">{label}</div>
          <div class="bar-track"><div class="{fill_class}" style="width:{pct}%;"></div></div>
          <div class="bar-count">{count}</div>
        </div>"""
    return html

# ─── MAIN APP ──────────────────────────────────────────────────────────────────

# Hero
st.markdown("""
<div class="hero">
  <h1>🧬 Biotech Early-Stage Funding Digest</h1>
  <p>Upload a PitchBook export → get an instant digest with deal leaderboard,
  oncology spotlight, and platform breakdown.<br>
  <span class="sub">Filter: Angel + Accelerator · Biotechnology + Drug Manufacturers</span></p>
</div>
""", unsafe_allow_html=True)

# File uploader
uploaded = st.file_uploader(
    "Drop your PitchBook 'All Columns' xlsx export here",
    type=["xlsx"],
    help="Export from PitchBook using the 'All Columns' template, filtered for Angel + Accelerator deals in Biotech + Drug Manufacturers"
)

if uploaded is None:
    st.markdown("""
    <div class="upload-zone">
      <h3>📂 Upload your PitchBook export to get started</h3>
      <p>Supports the standard PitchBook "All Columns" xlsx export.<br>
      Set your filters to: <strong>Deal Type = Angel + Accelerator/Incubator</strong> ·
      <strong>Industry = Biotechnology + Drug Manufacturers</strong> · Top 10 results.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Parse
with st.spinner("Parsing your PitchBook export..."):
    deals = parse_pitchbook(uploaded)

if not deals:
    st.stop()

# ── STATS ──
total_capital = sum(d["deal_size_raw"] for d in deals)
onc_count     = sum(1 for d in deals if d["is_onc"])
sizes         = sorted([d["deal_size_raw"] for d in deals if d["deal_size_raw"] > 0])
median        = sizes[len(sizes)//2] if sizes else 0
total_fmt     = f"${total_capital:.1f}M" if total_capital < 1000 else f"${total_capital/1000:.1f}B"
median_fmt    = f"${median:.1f}M" if median >= 1 else f"${median*1000:.0f}K"
date_str      = datetime.today().strftime("%B %d, %Y")

c1, c2, c3, c4 = st.columns(4)
for col, label, value, sub in [
    (c1, "Total deals",     str(len(deals)), "Angel + Accelerator"),
    (c2, "Total capital",   total_fmt,       "USD equivalent"),
    (c3, "Oncology tagged", str(onc_count),  f"{round(onc_count/len(deals)*100)}% of deals"),
    (c4, "Median deal",     median_fmt,      "Pre-seed range"),
]:
    col.markdown(f"""
    <div class="stat-box">
      <div class="stat-label">{label}</div>
      <div class="stat-value">{value}</div>
      <div class="stat-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── LEADERBOARD ──
st.markdown('<div class="section-title">Deal leaderboard — ranked by size</div>', unsafe_allow_html=True)
for i, d in enumerate(deals, 1):
    synopsis = (d["synopsis"][:250] + "…") if len(d["synopsis"]) > 250 else d["synopsis"]
    st.markdown(f"""
    <div class="deal-card">
      <div class="deal-header">
        <div class="deal-name"><span class="rank">{i}</span>{d['company']}</div>
        <div class="deal-amount">{d['deal_size']}</div>
      </div>
      <div class="deal-tags">{deal_tags(d)}</div>
      <div class="deal-desc">{synopsis or d['description'][:250]}</div>
    </div>""", unsafe_allow_html=True)

# ── ONCOLOGY SPOTLIGHT ──
onc_deals = [d for d in deals if d["is_onc"]]
st.markdown('<div class="section-title onc">Oncology spotlight</div>', unsafe_allow_html=True)
if onc_deals:
    for d in onc_deals:
        full = (d["synopsis"][:450] + "…") if len(d["synopsis"]) > 450 else d["synopsis"]
        deal_label = "Accelerator" if d["is_accel"] else "Angel"
        st.markdown(f"""
        <div class="onc-card">
          <div class="deal-header">
            <div class="onc-name">{d['company']}</div>
            <div class="onc-meta">{d['deal_size']} · {deal_label} · {d['geo']}</div>
          </div>
          <div class="deal-tags">
            {tag('Oncology','tag-onc')}
            {tag(d['modality'],'tag-stage')}
            {tag(d['biz_status'],'tag-accel') if d['biz_status'] else ''}
          </div>
          <div class="deal-desc">{full or d['description'][:450]}</div>
        </div>""", unsafe_allow_html=True)
else:
    st.info("No oncology-tagged deals in this batch.")

# ── CHARTS ──
col_mod, col_ta = st.columns(2)

with col_mod:
    st.markdown('<div class="section-title mod">Platform modality</div>', unsafe_allow_html=True)
    mod_counts = {}
    for d in deals:
        mod_counts[d["modality"]] = mod_counts.get(d["modality"], 0) + 1
    st.markdown(bar_chart(mod_counts, "bar-fill-mod"), unsafe_allow_html=True)

with col_ta:
    st.markdown('<div class="section-title ta">Therapeutic area</div>', unsafe_allow_html=True)
    ta_counts = {}
    for d in deals:
        ta_counts[d["ta"]] = ta_counts.get(d["ta"], 0) + 1
    st.markdown(bar_chart(ta_counts, "bar-fill-ta"), unsafe_allow_html=True)

# ── EMAIL SEND ──
st.markdown("---")
st.markdown('<div class="section-title">Send digest to email</div>', unsafe_allow_html=True)

col_email, col_btn = st.columns([3, 1])
with col_email:
    recipient = st.text_input(
        "Email address",
        placeholder="professor@hbs.edu",
        label_visibility="collapsed"
    )
with col_btn:
    send_clicked = st.button("Send digest", use_container_width=True, type="primary")

if send_clicked:
    if not recipient or "@" not in recipient:
        st.warning("Please enter a valid email address.")
    else:
        with st.spinner(f"Sending digest to {recipient}..."):
            html_email = build_email_html(deals, date_str)
            subject = f"Biotech Early-Stage Funding Digest — {date_str}"
            ok, msg = send_digest_email(recipient, subject, html_email)
        if ok:
            st.success(f"Sent! {msg}")
        else:
            st.error(f"Send failed: {msg}")
            if "not configured" in msg:
                st.info("""**To enable email sending, add these to Streamlit Cloud Secrets:**
```
SENDGRID_API_KEY = "SG.your-key-here"
SENDGRID_FROM_EMAIL = "your-verified-email@gmail.com"
```
See DEPLOY.md for full setup instructions.""")

# ── FOOTER ──
st.markdown(f"""
<div class="footer">
  Compiled by Biotech Early-Stage Digest · Powered by Claude ·
  Source: PitchBook (Angel + Accelerator · Biotech + Drug Manufacturers · {date_str})
</div>""", unsafe_allow_html=True)
