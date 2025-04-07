import os
from fpdf import FPDF
from datetime import datetime
import requests
from io import BytesIO
from tempfile import NamedTemporaryFile

basepath = os.getcwd()


class CustomPDF(FPDF):
    def __init__(self, header_path, footer_path):
        super().__init__()
        self.header_img = header_path
        self.footer_img = footer_path

    def header(self):
        if self.header_img and os.path.exists(self.header_img):
            self.image(self.header_img, x=0, y=0, w=210)
            self.ln(35)

    def footer(self):
        if self.footer_img and os.path.exists(self.footer_img):
            self.set_y(-30)
            self.image(self.footer_img, x=0, y=self.get_y(), w=210)

def generate_report(data):
    foundry = data["foundry"]
    defect = data.get("defect_type") or data.get("query", "").split("for")[-1].strip()
    reference_period = " to ".join(data["reference_period"])
    comparison_period = " to ".join(data["comparison_period"])
    top_param = data.get("top_parameter", "N/A")
    charts = data.get("charts", [])

    # Paths to header and footer images
    header_path = os.path.join(basepath, "results", "report", "header.png")
    footer_path = os.path.join(basepath, "results", "report", "footer.png")

    pdf = CustomPDF(header_path, footer_path)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_fill_color(135, 206, 250)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 12, "Fishbone Analytics Report", ln=True, align="C", fill=True, border=1)
    pdf.ln(8)

    # Metadata Table
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Analysis Metadata", ln=True)
    pdf.set_font("Arial", "", 11)
    meta_data = [
        ("Foundry", foundry),
        ("Defect Analyzed", defect),
        ("Reference Period", reference_period),
        ("Comparison Period", comparison_period),
        ("Top Varied Parameter", top_param),
    ]
    # if "query" in data:
    #     meta_data.append(("User Query", data["query"]))

    col_width = 50
    for key, value in meta_data:
        pdf.cell(col_width, 10, f"{key}:", border=1)
        pdf.cell(0, 10, str(value), border=1, ln=True)
    pdf.ln(5)

    # Chart titles (one per page)
    chart_titles = [
        " Monthly Rejection Trend",
        f" Fishbone Diagram for {defect}",
        f" Distribution Plot for {top_param}",
        f" Box Plot for {top_param}",
        f" Correlation Plot for {top_param}",
        f" Summary Table Plot"
    ]

    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(0, 0, 128)

    for i, chart_url in enumerate(charts):
        title = chart_titles[i] if i < len(chart_titles) else f"📌 Chart {i + 1}"
        try:
            response = requests.get(chart_url)
            if response.status_code == 200:
                with NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                    tmp_file.write(response.content)
                    tmp_file.flush()

                    # New page for each image
                    pdf.add_page()
                    pdf.cell(0, 10, title, ln=True, align="C")
                    pdf.ln(5)
                    pdf.image(tmp_file.name, x=15, w=180)
                    pdf.ln(5)
            else:
                print(f"[!] Failed to fetch image (status {response.status_code}): {chart_url}")
        except Exception as e:
            print(f"[!] Exception while downloading image {chart_url}: {e}")

    # Save the report
    report_dir = os.path.join("results", foundry, "reports")
    os.makedirs(report_dir, exist_ok=True)
    report_filename = f"Fishbone_Report_{defect.replace(' ', '_')}_{datetime.now().strftime('%d-%m-%Y')}.pdf"
    report_path = os.path.join(report_dir, report_filename)
    pdf.output(report_path)

    return report_path
