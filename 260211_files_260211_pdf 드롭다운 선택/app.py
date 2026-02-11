"""
Shipping Mark PDF 웹앱
- 국가별 프로필 선택
- PDF 업로드 후 페이지 번호, 주소, 기타 정보 오버레이
- 다중 배치 처리 및 최종 합본 PDF 생성
- 좌표 미세 조정 가능
"""

from flask import Flask, render_template, request, send_file, jsonify
from PyPDF4 import PdfFileReader, PdfFileWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.colors import black, white
from reportlab.lib.units import mm
import io
import os
import json
import tempfile
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "pdf")      # PDF 원본 파일 폴더
PIC_DIR = os.path.join(BASE_DIR, "pic")      # 이미지 파일 폴더

os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(PIC_DIR, exist_ok=True)

# ─── 국가별 프로필 정의 ───────────────────────────────────────────────
# 각 프로필은 기존 .py 파일의 좌표/설정을 default 값으로 보존
COUNTRY_PROFILES = {
    "afghanistan": {
        "name": "아프간",
        "description": "ZALAND SARSABZ LTD. - 표준 주소 오버레이",
        "pagesize": "letter",
        "address_type": "selectable",
        "defaults": {
            "page_num_x": 238,
            "page_num_y": 45,
            "page_num_gap": 1,
            "address_rect_x": 202,
            "address_rect_y": 457,
            "address_rect_w": 500,
            "address_rect_h": 19,
            "address_text_x": 202,
            "address_text_y": 459,
        },
        "extra_fields": [],
    },
    "oman": {
        "name": "오만",
        "description": "HUZAIFA GENERAL TRADING LLC - consignee 변경 포함",
        "pagesize": "landscape_letter",
        "address_type": "fixed",
        "fixed_address": "JEBEL ALI FREE ZONE JAFZA DUBAI UAE PO BOX 261243",
        "defaults": {
            "page_num_x": 234,
            "page_num_y": 45,
            "page_num_gap": 25,
            "address_rect_x": 201,
            "address_rect_y": 457,
            "address_rect_w": 500,
            "address_rect_h": 18,
            "address_text_x": 201,
            "address_text_y": 459,
            # consignee 영역 (기존 부분 가리고 새 이름 입력)
            "consignee_hide_rect_x": 201,
            "consignee_hide_rect_y": 493,
            "consignee_hide_rect_w": 500,
            "consignee_hide_rect_h": 18,
            "consignee_text_x": 201,
            "consignee_text_y": 495,
            "consignee_name": "HUZAIFA GENERAL TRADING LLC",
        },
        "extra_fields": ["consignee"],
    },
    "uzbek": {
        "name": "우즈벡",
        "description": "ALLMED FZCO - 표준 주소 오버레이",
        "pagesize": "letter",
        "address_type": "selectable",
        "defaults": {
            "page_num_x": 238,
            "page_num_y": 45,
            "page_num_gap": 24,
            "address_rect_x": 202,
            "address_rect_y": 458,
            "address_rect_w": 500,
            "address_rect_h": 15,
            "address_text_x": 202,
            "address_text_y": 458,
        },
        "extra_fields": [],
    },
    "chile": {
        "name": "칠레",
        "description": "BOOSTIN ADVANCE - 등록번호 및 제품명 변경 포함",
        "pagesize": "landscape_letter",
        "address_type": "fixed",
        "fixed_address": "Almirante Pastene 300, Providencia, Santiago, Chile",
        "defaults": {
            "page_num_x": 234,
            "page_num_y": 45,
            "page_num_gap": 25,
            "address_rect_x": 201,
            "address_rect_y": 456,
            "address_rect_w": 500,
            "address_rect_h": 23,
            "address_text_x": 201,
            "address_text_y": 457,
            # 등록번호
            "reg_rect_x": 201,
            "reg_rect_y": 120,
            "reg_rect_w": 500,
            "reg_rect_h": 15,
            "reg_text_x": 201,
            "reg_text_y": 120,
            "reg_text": "Registered : N° 2477-B",
            # 제품명 변경
            "product_hide_rect_x": 201,
            "product_hide_rect_y": 353,
            "product_hide_rect_w": 500,
            "product_hide_rect_h": 22,
            "product_text_x": 201,
            "product_text_y": 355,
            "product_name": "BOOSTIN ADVANCE",
        },
        "extra_fields": ["registration", "product_name"],
    },
    "mexico": {
        "name": "멕시코",
        "description": "표준 주소 오버레이",
        "pagesize": "letter",
        "address_type": "selectable",
        "defaults": {
            "page_num_x": 238,
            "page_num_y": 45,
            "page_num_gap": 24,
            "address_rect_x": 202,
            "address_rect_y": 455,
            "address_rect_w": 500,
            "address_rect_h": 20,
            "address_text_x": 202,
            "address_text_y": 459,
        },
        "extra_fields": [],
    },
    "brazil_etc": {
        "name": "브라질 외",
        "description": "브라질 외 기타 국가 - 표준 주소 오버레이 (좌표 상이)",
        "pagesize": "letter",
        "address_type": "selectable",
        "defaults": {
            "page_num_x": 238,
            "page_num_y": 50,
            "page_num_gap": 24,
            "address_rect_x": 218,
            "address_rect_y": 440,
            "address_rect_w": 500,
            "address_rect_h": 15,
            "address_text_x": 218,
            "address_text_y": 440,
        },
        "extra_fields": [],
    },
    "brazil": {
        "name": "브라질",
        "description": "OUROFINO - 바코드 이미지, 배치번호, consignee/제품명/박스텍스트 변경",
        "pagesize": "letter",
        "address_type": "fixed",
        "fixed_address": "RODOVIA ANHANGUERA SSP330 KM298, ZIP CODE: 14140-000, CRAVINHOS - SÃO PAULO - Brazil",
        "defaults": {
            "page_num_x": 238,
            "page_num_y": 45,
            "page_num_gap": 24,
            "address_rect_x": 201,
            "address_rect_y": 458,
            "address_rect_w": 500,
            "address_rect_h": 15,
            "address_text_x": 201,
            "address_text_y": 458,
            # 배치 번호
            "batch_text_x": 286,
            "batch_text_y": 290,
            # consignee 변경
            "consignee_hide_rect_x": 201,
            "consignee_hide_rect_y": 492,
            "consignee_hide_rect_w": 500,
            "consignee_hide_rect_h": 15,
            "consignee_text_x": 201,
            "consignee_text_y": 492,
            "consignee_name": "OUROFINO AGRONEGOCIO LTDA",
            # 제품명 변경
            "product_hide_rect_x": 201,
            "product_hide_rect_y": 351,
            "product_hide_rect_w": 500,
            "product_hide_rect_h": 24,
            "product_text_x": 201,
            "product_text_y": 356,
            "product_name": "INJECTOR",
            # 박스 텍스트 변경
            "box_text_hide_rect_x": 201,
            "box_text_hide_rect_y": 320,
            "box_text_hide_rect_w": 500,
            "box_text_hide_rect_h": 22,
            "box_text_x": 201,
            "box_text_y": 323,
            "box_text": "900 Syringe / Carton",
            # 바코드/QR 이미지
            "barcode_x": 183,
            "barcode_y": 92,
            "barcode_w": 110,
            "barcode_h": 60,
        },
        "extra_fields": ["batch_number", "consignee", "product_name", "box_text", "barcode"],
    },
}

# 선택 가능한 주소 목록 (selectable 타입 국가에서 사용)
SELECTABLE_ADDRESSES = [
    {"label": "페루", "value": "RUC: 20109333159 AV. DE LAS ARTES NORTE NRO. 310, SAN BORJA, LIMA - PERU"},
    {"label": "우즈벡 (ALLMED)", "value": "ALLMED FZCO.   P.O. BOX No. 261257 JAFZA, Dubai, U.A.E."},
    {"label": "오만 (SMARK)", "value": "SMARK FZE JEBAL ALI JAFZA SOUTH LIU10, BD 06, P.O. Box 18076, DUBAI, UAE"},
    {"label": "아프간", "value": "ZALAND SARSABZ LTD.  1st floor, Kabul Plaza Jadai Maiwand closed to kochi Barana, Kabul Afghanistan"},
    {"label": "멕시코", "value": "Av. San Jerónimo #369, Col. La Otra, Del. Alvaro Obregón, C.P 01090, Ciudad de México, México"},
    {"label": "남아공/케냐 (주소 수정 불필요)", "value": "__SKIP__"},
]


def get_pagesize(profile_key):
    """프로필에 맞는 페이지 사이즈 반환"""
    ps = COUNTRY_PROFILES[profile_key]["pagesize"]
    if ps == "landscape_letter":
        return landscape(letter)
    return letter


def copy_pages(input_pdf_bytes, num_copies):
    """
    PDF 바이트에서 페이지를 복사.
    - 1페이지 PDF: num_copies 만큼 첫 페이지 복사
    - 2페이지 PDF: (num_copies - 1)만큼 첫 페이지 복사 + 마지막에 2페이지 추가
    """
    reader = PdfFileReader(io.BytesIO(input_pdf_bytes))
    writer = PdfFileWriter()
    total_pages = reader.getNumPages()

    if total_pages not in [1, 2]:
        raise ValueError(f"지원하지 않는 페이지 수: {total_pages}. 1페이지 또는 2페이지 PDF만 지원됩니다.")

    actual_copies = num_copies
    if total_pages == 2:
        actual_copies -= 1

    for _ in range(actual_copies):
        writer.addPage(reader.getPage(0))
    if total_pages == 2:
        writer.addPage(reader.getPage(1))

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


def build_page_number_text(box_num, total, gap):
    """페이지 번호 텍스트 생성 (간격 조절 가능)"""
    spaces = " " * gap
    return f"{box_num}{spaces}{total}"


def process_pdf(input_pdf_bytes, profile_key, params, current_doc_num, total_docs):
    """
    PDF에 오버레이(페이지 번호, 주소, 기타)를 적용.
    params: 사용자가 조정한 좌표 및 설정값 dict
    """
    reader = PdfFileReader(io.BytesIO(input_pdf_bytes))
    writer = PdfFileWriter()
    total_pages = reader.getNumPages()
    profile = COUNTRY_PROFILES[profile_key]
    pagesize = get_pagesize(profile_key)

    address = params.get("address", "")
    skip_address = (address == "__SKIP__") or params.get("skip_address", False)
    batch_number = params.get("batch_number", "")

    for i in range(total_pages):
        page = reader.getPage(i)
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=pagesize)

        # ── 1) 페이지 번호 ────────────────────────────────
        page_num_text = build_page_number_text(
            current_doc_num + i,
            total_docs,
            int(params.get("page_num_gap", profile["defaults"]["page_num_gap"]))
        )
        can.drawString(
            float(params.get("page_num_x", profile["defaults"]["page_num_x"])),
            float(params.get("page_num_y", profile["defaults"]["page_num_y"])),
            page_num_text
        )

        # ── 2) 주소 오버레이 ──────────────────────────────
        if not skip_address and address:
            can.setFillColor(white)
            can.rect(
                float(params.get("address_rect_x", profile["defaults"]["address_rect_x"])),
                float(params.get("address_rect_y", profile["defaults"]["address_rect_y"])),
                float(params.get("address_rect_w", profile["defaults"]["address_rect_w"])),
                float(params.get("address_rect_h", profile["defaults"]["address_rect_h"])),
                fill=True, stroke=False
            )
            can.setFillColor(black)
            can.drawString(
                float(params.get("address_text_x", profile["defaults"]["address_text_x"])),
                float(params.get("address_text_y", profile["defaults"]["address_text_y"])),
                address
            )

        # ── 3) 국가별 추가 처리 ──────────────────────────

        # --- consignee 변경 (오만, 브라질) ---
        if "consignee" in profile.get("extra_fields", []):
            consignee_name = params.get("consignee_name", profile["defaults"].get("consignee_name", ""))
            if consignee_name:
                can.setFillColor(white)
                can.rect(
                    float(params.get("consignee_hide_rect_x", profile["defaults"]["consignee_hide_rect_x"])),
                    float(params.get("consignee_hide_rect_y", profile["defaults"]["consignee_hide_rect_y"])),
                    float(params.get("consignee_hide_rect_w", profile["defaults"]["consignee_hide_rect_w"])),
                    float(params.get("consignee_hide_rect_h", profile["defaults"]["consignee_hide_rect_h"])),
                    fill=True, stroke=False
                )
                can.setFillColor(black)
                can.drawString(
                    float(params.get("consignee_text_x", profile["defaults"]["consignee_text_x"])),
                    float(params.get("consignee_text_y", profile["defaults"]["consignee_text_y"])),
                    consignee_name
                )

        # --- 등록번호 (칠레) ---
        if "registration" in profile.get("extra_fields", []):
            reg_text = params.get("reg_text", profile["defaults"].get("reg_text", ""))
            if reg_text:
                can.setFillColor(white)
                can.rect(
                    float(params.get("reg_rect_x", profile["defaults"]["reg_rect_x"])),
                    float(params.get("reg_rect_y", profile["defaults"]["reg_rect_y"])),
                    float(params.get("reg_rect_w", profile["defaults"]["reg_rect_w"])),
                    float(params.get("reg_rect_h", profile["defaults"]["reg_rect_h"])),
                    fill=True, stroke=False
                )
                can.setFillColor(black)
                can.drawString(
                    float(params.get("reg_text_x", profile["defaults"]["reg_text_x"])),
                    float(params.get("reg_text_y", profile["defaults"]["reg_text_y"])),
                    reg_text
                )

        # --- 제품명 변경 (칠레, 브라질) ---
        if "product_name" in profile.get("extra_fields", []):
            product_name = params.get("product_name", profile["defaults"].get("product_name", ""))
            if product_name:
                can.setFillColor(white)
                can.rect(
                    float(params.get("product_hide_rect_x", profile["defaults"]["product_hide_rect_x"])),
                    float(params.get("product_hide_rect_y", profile["defaults"]["product_hide_rect_y"])),
                    float(params.get("product_hide_rect_w", profile["defaults"]["product_hide_rect_w"])),
                    float(params.get("product_hide_rect_h", profile["defaults"]["product_hide_rect_h"])),
                    fill=True, stroke=False
                )
                can.setFillColor(black)
                can.drawString(
                    float(params.get("product_text_x", profile["defaults"]["product_text_x"])),
                    float(params.get("product_text_y", profile["defaults"]["product_text_y"])),
                    product_name
                )

        # --- 박스 텍스트 변경 (브라질) ---
        if "box_text" in profile.get("extra_fields", []):
            box_text = params.get("box_text", profile["defaults"].get("box_text", ""))
            if box_text:
                can.setFillColor(white)
                can.rect(
                    float(params.get("box_text_hide_rect_x", profile["defaults"]["box_text_hide_rect_x"])),
                    float(params.get("box_text_hide_rect_y", profile["defaults"]["box_text_hide_rect_y"])),
                    float(params.get("box_text_hide_rect_w", profile["defaults"]["box_text_hide_rect_w"])),
                    float(params.get("box_text_hide_rect_h", profile["defaults"]["box_text_hide_rect_h"])),
                    fill=True, stroke=False
                )
                can.setFillColor(black)
                can.drawString(
                    float(params.get("box_text_x", profile["defaults"]["box_text_x"])),
                    float(params.get("box_text_y", profile["defaults"]["box_text_y"])),
                    box_text
                )

        # --- 배치 번호 (브라질) ---
        if "batch_number" in profile.get("extra_fields", []) and batch_number:
            batch_display = f"(  {batch_number}  )"
            can.drawString(
                float(params.get("batch_text_x", profile["defaults"]["batch_text_x"])),
                float(params.get("batch_text_y", profile["defaults"]["batch_text_y"])),
                batch_display
            )

        # --- 바코드/QR 이미지 (브라질) ---
        if "barcode" in profile.get("extra_fields", []):
            barcode_path = os.path.join(PIC_DIR, "boostin.png")
            if os.path.exists(barcode_path):
                try:
                    bx = float(params.get("barcode_x", profile["defaults"]["barcode_x"]))
                    by = float(params.get("barcode_y", profile["defaults"]["barcode_y"]))
                    bw = float(params.get("barcode_w", profile["defaults"]["barcode_w"]))
                    bh = float(params.get("barcode_h", profile["defaults"]["barcode_h"]))
                    can.drawImage(barcode_path, bx, by, width=bw, height=bh,
                                  preserveAspectRatio=True, mask='auto')
                except Exception as e:
                    print(f"바코드 이미지 추가 실패: {e}")

        can.save()
        packet.seek(0)
        overlay_pdf = PdfFileReader(packet)
        page.mergePage(overlay_pdf.getPage(0))
        writer.addPage(page)

    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read(), total_pages


# ─── Flask 라우트 ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html",
                           profiles=COUNTRY_PROFILES,
                           addresses=SELECTABLE_ADDRESSES)


@app.route("/api/profiles")
def api_profiles():
    """프로필 정보 API (프론트엔드에서 동적 폼 구성용)"""
    return jsonify(COUNTRY_PROFILES)


@app.route("/api/addresses")
def api_addresses():
    """선택 가능 주소 목록 API"""
    return jsonify(SELECTABLE_ADDRESSES)


@app.route("/api/pdf_files")
def api_pdf_files():
    """pdf/ 폴더 내 PDF 파일 목록 API"""
    pdf_files = sorted([
        f for f in os.listdir(PDF_DIR)
        if f.lower().endswith('.pdf')
    ])
    return jsonify(pdf_files)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """PDF 생성 API"""
    try:
        profile_key = request.form.get("profile")
        if profile_key not in COUNTRY_PROFILES:
            return jsonify({"error": f"알 수 없는 프로필: {profile_key}"}), 400

        profile = COUNTRY_PROFILES[profile_key]
        total_boxes = int(request.form.get("total_boxes", 0))
        if total_boxes <= 0:
            return jsonify({"error": "전체 박스 수는 1 이상이어야 합니다."}), 400

        # 배치 정보 파싱
        batch_count = int(request.form.get("batch_count", 0))
        if batch_count <= 0:
            return jsonify({"error": "최소 1개의 배치가 필요합니다."}), 400

        # 좌표 파라미터 수집
        params = {}
        for key in profile["defaults"]:
            val = request.form.get(key)
            if val is not None and val != "":
                params[key] = val

        # 고정 주소 처리
        if profile["address_type"] == "fixed":
            params["address"] = request.form.get("address", profile.get("fixed_address", ""))
        params["skip_address"] = request.form.get("skip_address") == "true"

        # 국가별 추가 텍스트 파라미터
        for field in ["consignee_name", "reg_text", "product_name", "box_text"]:
            val = request.form.get(field)
            if val is not None:
                params[field] = val

        # 배치별 처리
        combined_writer = PdfFileWriter()
        current_doc_num = 1

        for b in range(batch_count):
            pdf_filename = request.form.get(f"pdf_{b}")
            if not pdf_filename:
                return jsonify({"error": f"배치 {b+1}의 PDF 파일을 선택하세요."}), 400

            pdf_path = os.path.join(PDF_DIR, pdf_filename)
            if not os.path.isfile(pdf_path):
                return jsonify({"error": f"배치 {b+1}: 파일을 찾을 수 없습니다 - {pdf_filename}"}), 400

            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            copies = int(request.form.get(f"copies_{b}", 1))
            batch_number = request.form.get(f"batch_number_{b}", "")
            batch_address = request.form.get(f"address_{b}", "")

            # 배치별 주소 처리
            batch_params = dict(params)
            if profile["address_type"] == "selectable":
                if batch_address == "__SKIP__":
                    batch_params["skip_address"] = True
                    batch_params["address"] = ""
                else:
                    batch_params["address"] = batch_address
                    batch_params["skip_address"] = False

            if batch_number:
                batch_params["batch_number"] = batch_number

            # 남은 박스 수 체크
            remaining = total_boxes - current_doc_num + 1
            if copies > remaining:
                return jsonify({
                    "error": f"배치 {b+1}: 요청 {copies}장이 남은 박스 수 {remaining}보다 많습니다."
                }), 400

            # 페이지 복사
            copied_bytes = copy_pages(pdf_bytes, copies)

            # 오버레이 적용
            processed_bytes, pages_added = process_pdf(
                copied_bytes, profile_key, batch_params, current_doc_num, total_boxes
            )

            # 합본에 추가
            processed_reader = PdfFileReader(io.BytesIO(processed_bytes))
            for p in range(processed_reader.getNumPages()):
                combined_writer.addPage(processed_reader.getPage(p))

            current_doc_num += pages_added

        # 최종 합본 PDF 생성
        output_buf = io.BytesIO()
        combined_writer.write(output_buf)
        output_buf.seek(0)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"shipping_mark_{profile['name']}_{timestamp}.pdf"

        return send_file(
            output_buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"처리 중 오류 발생: {str(e)}"}), 500


@app.route("/api/preview", methods=["POST"])
def api_preview():
    """미리보기용 첫 페이지 PDF 생성"""
    try:
        profile_key = request.form.get("profile")
        if profile_key not in COUNTRY_PROFILES:
            return jsonify({"error": f"알 수 없는 프로필: {profile_key}"}), 400

        profile = COUNTRY_PROFILES[profile_key]
        total_boxes = int(request.form.get("total_boxes", 1))

        pdf_filename = request.form.get("pdf_0")
        if not pdf_filename:
            return jsonify({"error": "미리보기를 위해 첫 번째 배치의 PDF를 선택하세요."}), 400

        pdf_path = os.path.join(PDF_DIR, pdf_filename)
        if not os.path.isfile(pdf_path):
            return jsonify({"error": f"파일을 찾을 수 없습니다 - {pdf_filename}"}), 400

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        # 좌표 파라미터 수집
        params = {}
        for key in profile["defaults"]:
            val = request.form.get(key)
            if val is not None and val != "":
                params[key] = val

        # 주소
        if profile["address_type"] == "fixed":
            params["address"] = request.form.get("address", profile.get("fixed_address", ""))
        else:
            batch_address = request.form.get("address_0", "")
            if batch_address == "__SKIP__":
                params["skip_address"] = True
                params["address"] = ""
            else:
                params["address"] = batch_address

        # 추가 텍스트 파라미터
        for field in ["consignee_name", "reg_text", "product_name", "box_text"]:
            val = request.form.get(field)
            if val is not None:
                params[field] = val

        batch_number = request.form.get("batch_number_0", "")
        if batch_number:
            params["batch_number"] = batch_number

        # 첫 페이지만 처리 (1장 복사)
        reader = PdfFileReader(io.BytesIO(pdf_bytes))
        writer = PdfFileWriter()
        writer.addPage(reader.getPage(0))
        buf = io.BytesIO()
        writer.write(buf)
        buf.seek(0)
        single_page_bytes = buf.read()

        processed_bytes, _ = process_pdf(
            single_page_bytes, profile_key, params, 1, total_boxes
        )

        return send_file(
            io.BytesIO(processed_bytes),
            mimetype="application/pdf",
            as_attachment=False,
            download_name="preview.pdf"
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"미리보기 오류: {str(e)}"}), 500


if __name__ == "__main__":
    print("=" * 60)
    print("  Shipping Mark PDF 웹앱")
    print("  http://127.0.0.1:5000 에서 접속하세요")
    print("=" * 60)
    app.run(debug=True, host="127.0.0.1", port=5000)
