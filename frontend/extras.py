"""Extra UI features for SemiBot analysis page:
   - Clearbit company logos next to ticker selection
   - Deep-link / copy-link support via ?ticker=... query param
   - PDF export of analysis results via fpdf2
"""
import io
import streamlit as st

# Ticker -> company domain for Clearbit free logo API.
# Only US / Western-listed companies have clean domains; keep a sensible
# fallback for the rest so the UI always renders something.
TICKER_DOMAINS = {
    "NVDA": "nvidia.com", "AMD": "amd.com", "INTC": "intel.com",
    "QCOM": "qualcomm.com", "AVGO": "broadcom.com", "MRVL": "marvell.com",
    "ARM": "arm.com", "ASML": "asml.com", "AMAT": "appliedmaterials.com",
    "LRCX": "lamresearch.com", "KLAC": "kla.com", "ONTO": "ontoinnovation.com",
    "ACMR": "acmrcsh.com", "MKSI": "mks.com", "TXN": "ti.com",
    "ADI": "analog.com", "MCHP": "microchip.com", "MPWR": "monolithicpower.com",
    "SWKS": "skyworksinc.com", "QRVO": "qorvo.com", "SLAB": "silabs.com",
    "SMTC": "semtech.com", "MU": "micron.com", "SNDK": "sandisk.com",
    "TSM": "tsmc.com", "GFS": "gf.com", "UMC": "umc.com",
    "ON": "onsemi.com", "STM": "st.com", "NXPI": "nxp.com",
    "ALGM": "allegromicro.com", "DIOD": "diodes.com", "ALAB": "asteralabs.com",
    "FORM": "formfactor.com", "RMBS": "rambus.com", "CRUS": "cirrus.com",
    "SITM": "sitime.com", "MTSI": "macom.com",
    "000660.KS": "skhynix.com", "005930.KS": "samsung.com",
    "2308.TW": "deltaww.com", "2454.TW": "mediatek.com",
    "3711.TW": "aseglobal.com",
    "6723.T": "renesas.com", "6857.T": "advantest.com",
    "8035.T": "tel.com", "285A.T": "kioxia.com",
    "IFX.DE": "infineon.com", "ASMI.AS": "asm.com", "BE.NA": "besi.com",
}

CLEARBIT_URL = "https://logo.clearbit.com/{domain}"


def logo_url(ticker: str) -> str | None:
    """Return the Clearbit logo URL for a ticker, or None if we don't have a mapping."""
    if not ticker:
        return None
    domain = TICKER_DOMAINS.get(ticker.upper())
    return CLEARBIT_URL.format(domain=domain) if domain else None


def render_ticker_logo(ticker: str, size: int = 48):
    """Render a company logo as inline HTML (silently drops if no mapping)."""
    url = logo_url(ticker)
    if not url:
        return
    st.markdown(
        f"""<div style="display:flex;justify-content:center;margin-top:12px;">
          <img src="{url}" alt="{ticker} logo" width="{size}" height="{size}"
               style="border-radius:8px;background:#fff;padding:6px;object-fit:contain;
                      box-shadow:0 2px 8px rgba(0,0,0,0.25);"
               onerror="this.style.display='none'" />
        </div>""",
        unsafe_allow_html=True,
    )


def get_ticker_from_query() -> str | None:
    """Read ?ticker=XXX from the URL for deep-linking."""
    try:
        tk = st.query_params.get("ticker", "")
        if isinstance(tk, list):
            tk = tk[0] if tk else ""
        return tk.upper().strip() or None
    except Exception:
        return None


def set_ticker_in_query(ticker: str):
    """Write ?ticker=XXX into the URL so the current analysis is shareable."""
    try:
        st.query_params["ticker"] = ticker
    except Exception:
        pass


def render_copy_link_button(ticker: str, base_url: str = "https://semibot-raj.streamlit.app/analysis"):
    """Small 'Copy link' button that copies the deep-link URL to clipboard."""
    url = f"{base_url}?ticker={ticker}"
    html = f"""
    <div style="display:flex;align-items:center;gap:8px;margin:8px 0;">
      <input id="sb-share-url" type="text" value="{url}" readonly
             style="flex:1;padding:8px 12px;border-radius:6px;border:1px solid #2A313D;
                    background:#171B21;color:#C7D1DF;font-family:monospace;font-size:12px;" />
      <button onclick="(function(){{
          var i=document.getElementById('sb-share-url');i.select();
          try{{navigator.clipboard.writeText(i.value);}}catch(e){{document.execCommand('copy');}}
          var b=this;b.innerText='Copied!';setTimeout(function(){{b.innerText='Copy link';}},1500);
        }}).call(this);"
        style="padding:8px 16px;border-radius:6px;border:1px solid #5B9BFF;
               background:#5B9BFF;color:#06101F;font-weight:600;cursor:pointer;font-size:12.5px;">
        Copy link
      </button>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def build_analysis_pdf(ticker: str, prediction: str, up_pct, down_pct,
                       scores: dict, reasoning: str, timestamp: str) -> bytes:
    """Build a branded PDF of a SemiBot analysis result. Returns raw PDF bytes."""
    from fpdf import FPDF  # fpdf2 - pure Python, no system deps

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(left=16, top=16, right=16)

    # Header
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(34, 50, 107)
    pdf.cell(0, 10, "SemiBot Analysis Report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 100, 120)
    pdf.cell(0, 6, f"Ticker: {ticker}  |  Generated: {timestamp}", ln=True)
    pdf.ln(4)

    # Prediction block
    pdf.set_fill_color(240, 242, 248)
    pdf.set_text_color(11, 13, 17)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 9, "Prediction", ln=True, fill=True)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(34, 50, 107)
    pdf.cell(0, 14, f"{prediction}", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(60, 70, 90)
    try:
        pdf.cell(0, 7, f"Up: {float(up_pct):.1f}%   Down: {float(down_pct):.1f}%", ln=True)
    except Exception:
        pass
    pdf.ln(4)

    # Factor scores
    if scores:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(11, 13, 17)
        pdf.cell(0, 8, "Factor Scores", ln=True)
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 10)
        for key, val in scores.items():
            label = str(key).replace("_", " ").title()
            try:
                v = float(val)
                color = (31, 122, 67) if v > 0 else (195, 54, 43) if v < 0 else (118, 122, 132)
                pdf.set_text_color(*color)
                pdf.cell(80, 6, label, border=0)
                pdf.cell(0, 6, f"{v:+.2f}", ln=True)
            except Exception:
                pdf.set_text_color(60, 70, 90)
                pdf.cell(80, 6, label, border=0)
                pdf.cell(0, 6, str(val)[:40], ln=True)
        pdf.ln(3)

    # Reasoning
    if reasoning:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(11, 13, 17)
        pdf.cell(0, 8, "Analysis", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(45, 55, 75)
        # fpdf2 doesn't support unicode by default; strip to latin-1-safe chars
        safe = reasoning.encode("latin-1", errors="replace").decode("latin-1")
        pdf.multi_cell(0, 5, safe)
        pdf.ln(3)

    # Footer
    pdf.set_y(-18)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(130, 140, 160)
    pdf.cell(0, 5, "SemiBot - Built by Raj Tejpal Khatik - MSc Applied AI, University of Warwick", ln=True, align="C")
    pdf.cell(0, 5, "Not financial advice. For academic / research use only.", ln=True, align="C")

    out = pdf.output(dest="S")
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return out.encode("latin-1")


def render_download_pdf_button(ticker: str, prediction: str, up_pct, down_pct,
                                scores: dict, reasoning: str, timestamp: str):
    """One-click 'Download PDF' button that builds and offers the PDF."""
    try:
        pdf_bytes = build_analysis_pdf(ticker, prediction, up_pct, down_pct, scores, reasoning, timestamp)
        st.download_button(
            label="Download PDF report",
            data=pdf_bytes,
            file_name=f"semibot_{ticker}_{timestamp.replace(':', '').replace(' ', '_')}.pdf",
            mime="application/pdf",
            use_container_width=False,
        )
    except ImportError:
        st.caption("PDF export unavailable (fpdf2 not installed — add `fpdf2` to requirements.txt)")
    except Exception as e:
        st.caption(f"PDF export failed: {e}")
