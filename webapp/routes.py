import time
from functools import wraps
from typing import Callable, Optional

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.auth import login_admin, login_pelanggan
from app.db import execute as raw_execute
from app.usage import create_usage, delete_usage, update_usage

from .db import get_db
from .midtrans import create_snap_token, get_snap_url, is_midtrans_enabled
from .queries import (
    create_customer,
    create_admin,
    update_admin,
    delete_admin,
    get_admin_stats,
    get_bill,
    get_usage,
    get_last_usage_for_customer, # Added for new feature
    list_bills,
    list_admins,
    list_recent_payments,
    list_monthly_reports,
    get_monthly_report,
    list_monthly_report_details,
    get_usage_by_customer_period,
    list_customers,
    list_tariffs,
    list_usages,
    get_default_admin_id,
    has_payment_for_bill,
    create_payment,
    update_bill_status,
    get_customer, # Import get_customer
)


def login_required(role: Optional[str] = None):
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("Akses ditolak.", "error")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def _matches_query(value: Optional[object], query: str) -> bool:
    if value is None:
        return False
    return query in str(value).lower()


def _row_matches(row: dict, query: str, fields: list, extra_values: Optional[list] = None) -> bool:
    for field in fields:
        if _matches_query(row.get(field), query):
            return True
    if extra_values:
        for value in extra_values:
            if _matches_query(value, query):
                return True
    return False


def _filter_rows(rows: list, query: str, fields: list, extra_values_fn: Optional[Callable] = None) -> list:
    if not query:
        return rows
    query = query.lower()
    filtered = []
    for row in rows:
        extra_values = extra_values_fn(row) if extra_values_fn else None
        if _row_matches(row, query, fields, extra_values):
            filtered.append(row)
    return filtered


def _suggest_from_rows(
    rows: list,
    query: str,
    fields: list,
    extra_values_fn: Optional[Callable] = None,
    limit: int = 8,
) -> list:
    if not query:
        return []
    query = query.lower()
    suggestions = []
    seen = set()
    for row in rows:
        extra_values = extra_values_fn(row) if extra_values_fn else None
        candidates = [row.get(field) for field in fields]
        if extra_values:
            candidates.extend(extra_values)
        for value in candidates:
            if value is None:
                continue
            text = str(value)
            if query in text.lower() and text not in seen:
                seen.add(text)
                suggestions.append(text)
                if len(suggestions) >= limit:
                    return suggestions
    return suggestions


def register_routes(app: Flask) -> None:
    @app.after_request
    def add_no_cache_headers(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.context_processor
    def inject_admin_notifications():
        if session.get("role") != "admin":
            return {}
        conn = get_db()
        notifications = list_recent_payments(conn, limit=20)
        return {
            "admin_notifications": notifications,
            "admin_notifications_count": len(notifications),
        }

    @app.route("/")
    def index():
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return render_template("landing.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            conn = get_db()
            user_admin = login_admin(conn, username, password)
            if user_admin:
                session.clear()
                session["user_id"] = int(user_admin["id_user"])
                session["username"] = user_admin["username"]
                session["name"] = user_admin["nama_admin"]
                session["role"] = "admin"
                flash("Login berhasil.", "success")
                return redirect(url_for("dashboard"))

            user_customer = login_pelanggan(conn, username, password)
            if user_customer:
                session.clear()
                session["user_id"] = int(user_customer["id_pelanggan"])
                session["username"] = user_customer["username"]
                session["name"] = user_customer["nama_pelanggan"]
                session["role"] = "pelanggan"
                flash("Login berhasil.", "success")
                return redirect(url_for("dashboard"))

            flash("Login gagal. Cek username atau password.", "error")

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required()
    def dashboard():
        conn = get_db()
        role = session.get("role")
        if role == "admin":
            stats = get_admin_stats(conn)
            bills = list_bills(conn)[:5]
            return render_template(
                "dashboard.html",
                role=role,
                stats=stats,
                bills=bills,
            )

        bills = list_bills(conn, id_pelanggan=session["user_id"])
        return render_template(
            "dashboard.html",
            role=role,
            bills=bills,
        )

    @app.route("/admin/usages")
    @login_required("admin")
    def admin_usages():
        conn = get_db()
        page = request.args.get("page", "1")
        query = request.args.get("q", "").strip()
        try:
            page_num = max(1, int(page))
        except ValueError:
            page_num = 1
        per_page = 5
        usages_all = list_usages(conn)
        usages_all = _filter_rows(
            usages_all,
            query,
            [
                "id_penggunaan",
                "id_pelanggan",
                "nama_pelanggan",
                "username",
                "bulan",
                "tahun",
                "meter_awal",
                "meter_akhir",
                "kwh",
            ],
            extra_values_fn=lambda row: [f"{row.get('bulan')}/{row.get('tahun')}"],
        )
        total_items = len(usages_all)
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        page_num = min(page_num, total_pages)
        start = (page_num - 1) * per_page
        end = start + per_page
        usages = usages_all[start:end]
        return render_template(
            "admin/usage_list.html",
            usages=usages,
            page=page_num,
            total_pages=total_pages,
            q=query,
        )

    @app.route("/admin/customers")
    @login_required("admin")
    def admin_customers():
        conn = get_db()
        page = request.args.get("page", "1")
        query = request.args.get("q", "").strip()
        try:
            page_num = max(1, int(page))
        except ValueError:
            page_num = 1
        per_page = 5
        customers_all = list_customers(conn)
        customers_all = _filter_rows(
            customers_all,
            query,
            [
                "id_pelanggan",
                "nama_pelanggan",
                "username",
                "nomor_kwh",
                "alamat",
                "id_tarif",
                "daya",
                "tarifperkwh",
            ],
            extra_values_fn=lambda row: [f"{row.get('daya')} VA"],
        )
        total_items = len(customers_all)
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        page_num = min(page_num, total_pages)
        start = (page_num - 1) * per_page
        end = start + per_page
        customers = customers_all[start:end]
        return render_template(
            "admin/customers.html",
            customers=customers,
            page=page_num,
            total_pages=total_pages,
            q=query,
        )

    @app.route("/admin/customers/new", methods=["GET", "POST"])
    @login_required("admin")
    def admin_customer_new():
        conn = get_db()
        tariffs = list_tariffs(conn)

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            nama_pelanggan = request.form.get("nama_pelanggan", "").strip()
            nomor_kwh = request.form.get("nomor_kwh", "").strip()
            alamat = request.form.get("alamat", "").strip()
            try:
                id_tarif = int(request.form.get("id_tarif", "0"))
            except ValueError:
                id_tarif = 0

            if not all([username, password, nama_pelanggan, nomor_kwh, alamat]) or id_tarif <= 0:
                flash("Semua field wajib diisi.", "error")
                return render_template("admin/customer_form.html", tariffs=tariffs)

            try:
                create_customer(
                    conn,
                    username,
                    password,
                    nama_pelanggan,
                    nomor_kwh,
                    alamat,
                    id_tarif,
                )
            except Exception as exc:
                flash(f"Gagal menambah pelanggan: {exc}", "error")
                return render_template("admin/customer_form.html", tariffs=tariffs)

            flash("Pelanggan berhasil ditambahkan.", "success")
            return redirect(url_for("admin_customers"))

        return render_template("admin/customer_form.html", tariffs=tariffs)

    @app.route("/admin/admins", methods=["GET", "POST"])
    @login_required("admin")
    def admin_admins():
        conn = get_db()
        page = request.args.get("page", "1")
        query = request.args.get("q", "").strip()
        try:
            page_num = max(1, int(page))
        except ValueError:
            page_num = 1
        per_page = 5
        admins_all = list_admins(conn)
        admins_all = _filter_rows(
            admins_all,
            query,
            [
                "id_user",
                "username",
                "nama_admin",
                "id_level",
            ],
        )
        total_items = len(admins_all)
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        page_num = min(page_num, total_pages)
        start = (page_num - 1) * per_page
        end = start + per_page
        admins = admins_all[start:end]

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            nama_admin = request.form.get("nama_admin", "").strip()
            try:
                id_level = int(request.form.get("id_level", "1"))
            except ValueError:
                id_level = 0

            if not all([username, password, nama_admin]) or id_level <= 0:
                flash("Semua field wajib diisi.", "error")
                return render_template(
                    "admin/admins.html",
                    admins=admins,
                    page=page_num,
                    total_pages=total_pages,
                    q=query,
                )

            try:
                create_admin(conn, username, password, nama_admin, id_level)
            except Exception as exc:
                flash(f"Gagal menambah admin: {exc}", "error")
                return render_template(
                    "admin/admins.html",
                    admins=admins,
                    page=page_num,
                    total_pages=total_pages,
                    q=query,
                )

            flash("Admin berhasil ditambahkan.", "success")
            return redirect(url_for("admin_admins"))

        return render_template(
            "admin/admins.html",
            admins=admins,
            page=page_num,
            total_pages=total_pages,
            q=query,
        )

    @app.route("/admin/admins/<int:admin_id>/edit", methods=["POST"])
    @login_required("admin")
    def admin_admin_edit(admin_id: int):
        conn = get_db()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        nama_admin = request.form.get("nama_admin", "").strip()
        try:
            id_level = int(request.form.get("id_level", "1"))
        except ValueError:
            id_level = 0

        if not all([username, nama_admin]) or id_level <= 0:
            flash("Semua field wajib diisi (kecuali password).", "error")
            return redirect(url_for("admin_admins"))

        try:
            update_admin(conn, admin_id, username, nama_admin, id_level, password or None)
        except Exception as exc:
            flash(f"Gagal mengubah admin: {exc}", "error")
            return redirect(url_for("admin_admins"))

        flash("Admin berhasil diperbarui.", "success")
        return redirect(url_for("admin_admins"))

    @app.route("/admin/admins/<int:admin_id>/delete", methods=["POST"])
    @login_required("admin")
    def admin_admin_delete(admin_id: int):
        conn = get_db()
        try:
            delete_admin(conn, admin_id)
        except Exception as exc:
            flash(f"Gagal menghapus admin: {exc}", "error")
            return redirect(url_for("admin_admins"))

        flash("Admin berhasil dihapus.", "success")
        return redirect(url_for("admin_admins"))

    @app.route("/admin/reports")
    @login_required("admin")
    def admin_reports():
        conn = get_db()
        page = request.args.get("page", "1")
        year_filter = request.args.get("year", "")
        month_filter = request.args.get("month", "")
        try:
            page_num = max(1, int(page))
        except ValueError:
            page_num = 1
        per_page = 5
        reports_all = list_monthly_reports(conn)
        if year_filter or month_filter:
            filtered = []
            for row in reports_all:
                if year_filter and str(row["tahun"]) != str(year_filter):
                    continue
                if month_filter and str(row["bulan"]) != str(month_filter):
                    continue
                filtered.append(row)
            reports_all = filtered
        total_items = len(reports_all)
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        page_num = min(page_num, total_pages)
        start = (page_num - 1) * per_page
        end = start + per_page
        reports = reports_all[start:end]
        years = sorted({row["tahun"] for row in reports_all}, reverse=True)
        return render_template(
            "admin/reports.html",
            reports=reports,
            page=page_num,
            total_pages=total_pages,
            years=years,
            year_filter=str(year_filter),
            month_filter=str(month_filter),
        )

    @app.route("/admin/reports/<int:year>/<int:month>/pdf")
    @login_required("admin")
    def admin_report_download(year: int, month: int):
        conn = get_db()
        report = get_monthly_report(conn, year, month)
        if not report:
            flash("Laporan tidak ditemukan.", "error")
            return redirect(url_for("admin_reports"))

        from io import BytesIO
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib import colors
        from flask import send_file
        from pathlib import Path

        details = list_monthly_report_details(conn, year, month)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()

        title_style = styles["Heading1"].clone("title_style")
        title_style.alignment = TA_CENTER

        elements = []

        logo_path = Path("assets/Logo-LSPBSI.png")
        if logo_path.exists():
            elements.append(Image(str(logo_path), width=1.2 * inch, height=1.2 * inch))
            elements.append(Spacer(1, 0.1 * inch))

        elements.append(Paragraph("LAPORAN BULANAN TAGIHAN LISTRIK", title_style))
        elements.append(Spacer(1, 0.25 * inch))

        month_names = [
            "Januari",
            "Februari",
            "Maret",
            "April",
            "Mei",
            "Juni",
            "Juli",
            "Agustus",
            "September",
            "Oktober",
            "November",
            "Desember",
        ]
        month_label = month_names[month - 1] if 1 <= month <= 12 else str(month)

        summary_data = [
            ["Keterangan", "Nilai"],
            ["Periode", f"{report['bulan']}/{report['tahun']}"],
            ["Total Pelanggan", str(report["total_pelanggan"])],
            ["Total Tagihan", str(report["total_tagihan"])],
            ["Tagihan Lunas", str(report["tagihan_lunas"])],
            ["Belum Bayar", str(report["tagihan_belum"])],
            [f"Total Pendapatan {month_label} {report['tahun']}", f"Rp {report['total_bayar']:,}".replace(",", ".")],
        ]

        table = Table(summary_data, colWidths=[2.8 * inch, 3.2 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f5b4a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    ("ALIGN", (1, 1), (1, -1), "LEFT"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#d9d2c9")),
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Spacer(1, 0.25 * inch))

        detail_header = [
            "No",
            "Nama Pelanggan",
            "No KWH",
            "Alamat",
            "Meter Awal",
            "Meter Akhir",
            "Jumlah Meter",
            "Tarif/kWh",
            "Total Bayar",
            "Status",
        ]
        detail_rows = [detail_header]
        for idx, row in enumerate(details, start=1):
            meter_awal = row.get("meter_awal")
            meter_akhir = row.get("meter_akhir")
            detail_rows.append(
                [
                    str(idx),
                    row.get("nama_pelanggan") or "-",
                    row.get("nomor_kwh") or "-",
                    row.get("alamat") or "-",
                    "-" if meter_awal is None else str(meter_awal),
                    "-" if meter_akhir is None else str(meter_akhir),
                    str(row.get("jumlah_meter") or 0),
                    f"Rp {row['tarifperkwh']:,}".replace(",", "."),
                    f"Rp {row['total_bayar']:,}".replace(",", "."),
                    row.get("status") or "-",
                ]
            )

        detail_col_widths = [0.45 * inch, 1.5 * inch, 1.0 * inch, 2.0 * inch, 0.85 * inch, 0.85 * inch, 0.95 * inch, 1.0 * inch, 1.1 * inch, 1.0 * inch]
        detail_table = Table(detail_rows, colWidths=detail_col_widths, repeatRows=1)
        detail_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f5b4a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9d2c9")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f2eb")]),
                ]
            )
        )
        elements.append(detail_table)

        footer_text = "Ringkasan berdasarkan data tagihan."
        printed_text = f"Tanggal Cetak: {time.strftime('%d-%m-%Y %H:%M:%S')}"

        def draw_footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 9)
            canvas.setFillColor(colors.grey)
            canvas.drawString(doc.leftMargin, 18, footer_text)
            canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 18, printed_text)
            canvas.restoreState()

        doc.build(elements, onFirstPage=draw_footer, onLaterPages=draw_footer)
        buffer.seek(0)

        filename = f"laporan_tagihan_{year}_{month:02d}.pdf"
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf",
        )

    @app.route("/admin/usages/new", methods=["GET", "POST"])
    @login_required("admin")
    def admin_usage_new():
        conn = get_db()
        customers = list_customers(conn)

        if request.method == "POST":
            try:
                id_pelanggan = int(request.form.get("id_pelanggan", "0"))
                bulan = int(request.form.get("bulan", "0"))
                tahun = int(request.form.get("tahun", "0"))
                meter_awal = int(request.form.get("meter_awal", "0"))
                meter_akhir = int(request.form.get("meter_akhir", "0"))
            except ValueError:
                flash("Input angka tidak valid.", "error")
                return render_template(
                    "admin/usage_form.html", customers=customers, usage=None
                )

            if meter_akhir < meter_awal:
                flash("Meter akhir harus lebih besar dari meter awal.", "error")
                return render_template(
                    "admin/usage_form.html", customers=customers, usage=None
                )

            create_usage(conn, id_pelanggan, bulan, tahun, meter_awal, meter_akhir)
            flash("Data penggunaan berhasil ditambahkan.", "success")
            return redirect(url_for("admin_usages"))

        return render_template("admin/usage_form.html", customers=customers, usage=None)

    @app.route("/admin/usages/<int:id_penggunaan>/edit", methods=["GET", "POST"])
    @login_required("admin")
    def admin_usage_edit(id_penggunaan: int):
        conn = get_db()
        customers = list_customers(conn)
        usage = get_usage(conn, id_penggunaan)
        if not usage:
            flash("Data penggunaan tidak ditemukan.", "error")
            return redirect(url_for("admin_usages"))

        if request.method == "POST":
            try:
                id_pelanggan = int(request.form.get("id_pelanggan", usage["id_pelanggan"]))
                bulan = int(request.form.get("bulan", usage["bulan"]))
                tahun = int(request.form.get("tahun", usage["tahun"]))
                meter_awal = int(request.form.get("meter_awal", usage["meter_awal"]))
                meter_akhir = int(request.form.get("meter_akhir", usage["meter_akhir"]))
            except ValueError:
                flash("Input angka tidak valid.", "error")
                return render_template(
                    "admin/usage_form.html", customers=customers, usage=usage
                )

            if meter_akhir < meter_awal:
                flash("Meter akhir harus lebih besar dari meter awal.", "error")
                return render_template(
                    "admin/usage_form.html", customers=customers, usage=usage
                )

            update_usage(conn, id_penggunaan, meter_awal, meter_akhir)
            if id_pelanggan != usage["id_pelanggan"] or bulan != usage["bulan"] or tahun != usage["tahun"]:
                execute_sql = (
                    "UPDATE penggunaan SET id_pelanggan = %s, bulan = %s, tahun = %s WHERE id_penggunaan = %s"
                )
                raw_execute(conn, execute_sql, (id_pelanggan, bulan, tahun, id_penggunaan))

            flash("Data penggunaan berhasil diperbarui.", "success")
            return redirect(url_for("admin_usages"))

        return render_template("admin/usage_form.html", customers=customers, usage=usage)

    @app.route("/admin/usages/<int:id_penggunaan>/delete", methods=["POST"])
    @login_required("admin")
    def admin_usage_delete(id_penggunaan: int):
        conn = get_db()
        delete_usage(conn, id_penggunaan)
        flash("Data penggunaan berhasil dihapus.", "success")
        return redirect(url_for("admin_usages"))

    @app.route("/admin/bills")
    @login_required("admin")
    def admin_bills():
        conn = get_db()
        status = request.args.get("status")
        page = request.args.get("page", "1")
        query = request.args.get("q", "").strip()
        try:
            page_num = max(1, int(page))
        except ValueError:
            page_num = 1
        status_filter = None
        if status == "unpaid":
            status_filter = "BELUM BAYAR"
        elif status == "paid":
            status_filter = "SUDAH BAYAR"
        per_page = 5
        bills_all = list_bills(conn, status=status_filter)
        bills_all = _filter_rows(
            bills_all,
            query,
            [
                "id_tagihan",
                "id_pelanggan",
                "nama_pelanggan",
                "username",
                "nomor_kwh",
                "bulan",
                "tahun",
                "jumlah_meter",
                "status",
                "tarifperkwh",
                "total_bayar",
            ],
            extra_values_fn=lambda row: [f"{row.get('bulan')}/{row.get('tahun')}"],
        )
        total_items = len(bills_all)
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        page_num = min(page_num, total_pages)
        start = (page_num - 1) * per_page
        end = start + per_page
        bills = bills_all[start:end]
        return render_template(
            "admin/bills.html",
            bills=bills,
            status=status,
            page=page_num,
            total_pages=total_pages,
            q=query,
        )

    @app.route("/admin/search-suggestions")
    @login_required("admin")
    def admin_search_suggestions():
        conn = get_db()
        section = request.args.get("section", "").strip().lower()
        query = request.args.get("q", "").strip()
        suggestions = []

        if section == "admins":
            rows = list_admins(conn)
            suggestions = _suggest_from_rows(
                rows,
                query,
                ["id_user", "username", "nama_admin", "id_level"],
            )
        elif section == "customers":
            rows = list_customers(conn)
            suggestions = _suggest_from_rows(
                rows,
                query,
                [
                    "id_pelanggan",
                    "nama_pelanggan",
                    "username",
                    "nomor_kwh",
                    "alamat",
                    "id_tarif",
                    "daya",
                    "tarifperkwh",
                ],
                extra_values_fn=lambda row: [f"{row.get('daya')} VA"],
            )
        elif section == "usages":
            rows = list_usages(conn)
            suggestions = _suggest_from_rows(
                rows,
                query,
                [
                    "id_penggunaan",
                    "id_pelanggan",
                    "nama_pelanggan",
                    "username",
                    "bulan",
                    "tahun",
                    "meter_awal",
                    "meter_akhir",
                    "kwh",
                ],
                extra_values_fn=lambda row: [f"{row.get('bulan')}/{row.get('tahun')}"],
            )
        elif section == "bills":
            status = request.args.get("status")
            status_filter = None
            if status == "unpaid":
                status_filter = "BELUM BAYAR"
            elif status == "paid":
                status_filter = "SUDAH BAYAR"
            rows = list_bills(conn, status=status_filter)
            suggestions = _suggest_from_rows(
                rows,
                query,
                [
                    "id_tagihan",
                    "id_pelanggan",
                    "nama_pelanggan",
                    "username",
                    "nomor_kwh",
                    "bulan",
                    "tahun",
                    "jumlah_meter",
                    "status",
                    "tarifperkwh",
                    "total_bayar",
                ],
                extra_values_fn=lambda row: [f"{row.get('bulan')}/{row.get('tahun')}"],
            )

        return jsonify({"suggestions": suggestions})

    @app.route("/admin/bills/new", methods=["GET", "POST"])
    @login_required("admin")
    def admin_bill_new():
        conn = get_db()
        customers = list_customers(conn)

        if request.method == "POST":
            try:
                id_pelanggan = int(request.form.get("id_pelanggan", "0"))
                bulan = int(request.form.get("bulan", "0"))
                tahun = int(request.form.get("tahun", "0"))
                meter_awal = int(request.form.get("meter_awal", "0"))
                meter_akhir = int(request.form.get("meter_akhir", "0"))
            except ValueError:
                flash("Input angka tidak valid.", "error")
                return render_template("admin/bill_form.html", customers=customers)

            if meter_akhir < meter_awal:
                flash("Meter akhir harus lebih besar dari meter awal.", "error")
                return render_template("admin/bill_form.html", customers=customers)

            create_usage(conn, id_pelanggan, bulan, tahun, meter_awal, meter_akhir)
            flash("Tagihan berhasil dibuat dari data penggunaan.", "success")
            return redirect(url_for("admin_bills"))

        return render_template("admin/bill_form.html", customers=customers)

    @app.route("/admin/bills/<int:id_tagihan>/mark-paid", methods=["POST"])
    @login_required("admin")
    def admin_bill_mark_paid(id_tagihan: int):
        conn = get_db()
        bill = get_bill(conn, id_tagihan)
        if bill:
            if not has_payment_for_bill(conn, id_tagihan):
                create_payment(
                    conn,
                    id_tagihan=id_tagihan,
                    id_pelanggan=bill["id_pelanggan"],
                    tanggal_pembayaran=time.strftime("%Y-%m-%d"),
                    bulan_bayar=int(bill["bulan"]),
                    biaya_admin=0.0,
                    total_bayar=float(bill["total_bayar"]),
                    id_user=int(session.get("user_id")),
                )
        update_bill_status(conn, id_tagihan, "SUDAH BAYAR")
        flash("Tagihan ditandai lunas.", "success")
        return redirect(url_for("admin_bills"))

    @app.route("/admin/customers/<int:customer_id>/history")
    @login_required("admin")
    def admin_customer_bill_history(customer_id: int):
        conn = get_db()
        customer = get_customer(conn, customer_id)
        if not customer:
            flash("Pelanggan tidak ditemukan.", "error")
            return redirect(url_for("admin_customers"))
        
        bills = list_bills(conn, id_pelanggan=customer_id)
        return render_template("admin/customer_bill_history.html", customer=customer, bills=bills)

    @app.route("/bills")
    @login_required("pelanggan")
    def customer_bills():
        conn = get_db()
        bills = list_bills(conn, id_pelanggan=session["user_id"])
        return render_template("customer/bills.html", bills=bills)

    @app.route("/pay/<int:id_tagihan>", methods=["GET"])
    @login_required("pelanggan")
    def pay_bill(id_tagihan: int):
        conn = get_db()
        bill = get_bill(conn, id_tagihan)
        if not bill or bill["id_pelanggan"] != session["user_id"]:
            flash("Tagihan tidak ditemukan.", "error")
            return redirect(url_for("customer_bills"))

        amount_raw = bill.get("total_bayar")
        if amount_raw is None:
            amount = int(bill.get("jumlah_meter") or 0)
        else:
            amount = int(float(amount_raw))
        order_id = f"INV-{id_tagihan}-{int(time.time())}"

        config = app.config
        snap_token = None
        midtrans_enabled = is_midtrans_enabled(config)
        error_message = None

        if midtrans_enabled:
            try:
                snap_token = create_snap_token(
                    config,
                    order_id,
                    amount,
                    {"name": bill["nama_pelanggan"]},
                )
            except Exception as exc:
                midtrans_enabled = False
                error_message = f"Gagal membuat transaksi Midtrans: {exc}"

        return render_template(
            "payment.html",
            bill=bill,
            amount=amount,
            order_id=order_id,
            snap_token=snap_token,
            midtrans_enabled=midtrans_enabled,
            snap_url=get_snap_url(config["MIDTRANS_IS_PRODUCTION"]),
            client_key=config["MIDTRANS_CLIENT_KEY"],
            error_message=error_message,
        )

    @app.route("/pay/<int:id_tagihan>/simulate", methods=["POST"])
    @login_required("pelanggan")
    def pay_bill_simulate(id_tagihan: int):
        conn = get_db()
        bill = get_bill(conn, id_tagihan)
        if not bill or bill["id_pelanggan"] != session["user_id"]:
            flash("Tagihan tidak ditemukan.", "error")
            return redirect(url_for("customer_bills"))

        if not has_payment_for_bill(conn, id_tagihan):
            admin_id = get_default_admin_id(conn)
            if admin_id:
                create_payment(
                    conn,
                    id_tagihan=id_tagihan,
                    id_pelanggan=bill["id_pelanggan"],
                    tanggal_pembayaran=time.strftime("%Y-%m-%d"),
                    bulan_bayar=int(bill["bulan"]),
                    biaya_admin=0.0,
                    total_bayar=float(bill["total_bayar"]),
                    id_user=admin_id,
                )
        update_bill_status(conn, id_tagihan, "SUDAH BAYAR")
        flash("Pembayaran simulasi berhasil.", "success")
        return redirect(url_for("customer_bills"))

    @app.route("/payments/notify", methods=["POST"])
    def payments_notify():
        payload = request.get_json(silent=True) or {}
        order_id = payload.get("order_id", "")
        transaction_status = payload.get("transaction_status", "")

        if not order_id or not transaction_status:
            return jsonify({"status": "invalid"}), 400

        parts = order_id.split("-")
        id_tagihan = None
        if len(parts) >= 2 and parts[1].isdigit():
            id_tagihan = int(parts[1])

        if not id_tagihan:
            return jsonify({"status": "invalid"}), 400

        if transaction_status in {"settlement", "capture", "success"}:
            conn = get_db()
            bill = get_bill(conn, id_tagihan)
            if bill and not has_payment_for_bill(conn, id_tagihan):
                admin_id = get_default_admin_id(conn)
                if admin_id:
                    create_payment(
                        conn,
                        id_tagihan=id_tagihan,
                        id_pelanggan=bill["id_pelanggan"],
                        tanggal_pembayaran=time.strftime("%Y-%m-%d"),
                        bulan_bayar=int(bill["bulan"]),
                        biaya_admin=0.0,
                        total_bayar=float(bill["total_bayar"]),
                        id_user=admin_id,
                    )
            update_bill_status(conn, id_tagihan, "SUDAH BAYAR")

        return jsonify({"status": "ok"})

    @app.route("/admin/api/get_last_usage/<int:customer_id>")
    @login_required("admin")
    def api_get_last_usage(customer_id: int):
        conn = get_db()
        last_usage = get_last_usage_for_customer(conn, customer_id)
        if last_usage:
            # Calculate next month and year based on the last usage
            # If current month is December (12), next month is January (1) of next year
            next_month = (last_usage['bulan'] % 12) + 1
            next_year = last_usage['tahun'] if last_usage['bulan'] < 12 else last_usage['tahun'] + 1
            
            return jsonify({
                "bulan": next_month,
                "tahun": next_year,
                "meter_awal": last_usage['meter_akhir']
            })
        # If no previous usage, return None for pre-fill fields
        return jsonify({"bulan": None, "tahun": None, "meter_awal": None})

    @app.route("/api/bill-details/<int:id_tagihan>")
    @login_required("pelanggan")
    def get_bill_details_api(id_tagihan: int):
        conn = get_db()
        bill = get_bill(conn, id_tagihan)
        if not bill or bill["id_pelanggan"] != session["user_id"]:
            return jsonify({"error": "Tagihan tidak ditemukan atau Anda tidak memiliki akses."}), 404
        return jsonify(bill)

    from io import BytesIO # Ensure BytesIO is imported
    from reportlab.lib.pagesizes import letter # Ensure letter is imported
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle # PageBreak removed as it's not used
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib import colors # Import colors
    from flask import send_file, current_app
    from pathlib import Path

    @app.route("/download-bill-proof/<int:id_tagihan>")
    @login_required("pelanggan")
    def download_bill_proof(id_tagihan: int):
        conn = get_db()
        bill = get_bill(conn, id_tagihan)

        if not bill or bill["id_pelanggan"] != session["user_id"]:
            flash("Tagihan tidak ditemukan atau Anda tidak memiliki akses.", "error")
            return redirect(url_for("customer_bills"))
        
        if bill["status"] != "SUDAH BAYAR":
            flash("Bukti pembayaran hanya tersedia untuk tagihan yang sudah dibayar.", "error")
            return redirect(url_for("customer_bills"))

        try:
            usage = get_usage_by_customer_period(conn, bill["id_pelanggan"], bill["bulan"], bill["tahun"])
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()

            style_title = styles["Heading1"].clone("style_title")
            style_title.fontSize = 18
            style_title.leading = 22
            style_title.alignment = TA_RIGHT
            style_title.fontName = "Helvetica-Bold"

            style_label = styles["Normal"].clone("style_label")
            style_label.fontSize = 10
            style_label.textColor = colors.HexColor("#6e6258")

            style_value = styles["Normal"].clone("style_value")
            style_value.fontSize = 11
            style_value.fontName = "Helvetica-Bold"

            style_section = styles["Heading2"].clone("style_section")
            style_section.fontSize = 12
            style_section.leading = 16
            style_section.textColor = colors.HexColor("#0f5b4a")

            elements = []

            logo_path = Path("assets/Logo-LSPBSI.png")
            logo_img = None
            if logo_path.exists():
                logo_img = Image(str(logo_path), width=1.1 * inch, height=1.1 * inch)

            header_left = logo_img if logo_img else ""
            header_center = Paragraph("<b>LSP Pascabayar</b><br/>Bukti Pembayaran Tagihan Listrik", styles["Normal"])
            header_right = Paragraph(f"INVOICE<br/><b>#{bill['id_tagihan']}</b>", style_title)

            header_table = Table(
                [[header_left, header_center, header_right]],
                colWidths=[1.3 * inch, 3.5 * inch, 1.7 * inch],
            )
            header_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            elements.append(header_table)
            elements.append(Spacer(1, 0.1 * inch))

            meta_table = Table(
                [
                    [
                        Paragraph("Tanggal Cetak", style_label),
                        Paragraph(time.strftime("%d-%m-%Y %H:%M:%S"), style_value),
                        Paragraph("Status", style_label),
                        Paragraph(bill["status"], style_value),
                    ]
                ],
                colWidths=[1.2 * inch, 2.0 * inch, 0.8 * inch, 1.5 * inch],
            )
            meta_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7f2eb")),
                        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#d9d2c9")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            elements.append(meta_table)
            elements.append(Spacer(1, 0.2 * inch))

            elements.append(Paragraph("Detail Pelanggan", style_section))
            customer_data = [
                ["Nama Pelanggan", bill["nama_pelanggan"]],
                ["Nomor KWH", bill["nomor_kwh"]],
                ["Alamat", bill["alamat"]],
            ]
            customer_table = Table(customer_data, colWidths=[1.7 * inch, 4.1 * inch])
            customer_table.setStyle(
                TableStyle(
                    [
                        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#6e6258")),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            elements.append(customer_table)
            elements.append(Spacer(1, 0.2 * inch))

            elements.append(Paragraph("Detail Tagihan", style_section))
            month_names = [
                "Januari",
                "Februari",
                "Maret",
                "April",
                "Mei",
                "Juni",
                "Juli",
                "Agustus",
                "September",
                "Oktober",
                "November",
                "Desember",
            ]
            month_index = bill["bulan"] - 1 if 1 <= bill["bulan"] <= 12 else None
            month_label = month_names[month_index] if month_index is not None else str(bill["bulan"])
            prev_month_index = (month_index - 1) if month_index is not None else None
            prev_month_label = month_names[prev_month_index] if prev_month_index is not None else "-"

            meter_awal = usage["meter_awal"] if usage else None
            meter_akhir = usage["meter_akhir"] if usage else None
            bill_data = [
                ["Periode", f"{month_label} {bill['tahun']}"],
                [f"Meter Akhir {prev_month_label}", "-" if meter_awal is None else str(meter_awal)],
                [f"Meter Akhir {month_label}", "-" if meter_akhir is None else str(meter_akhir)],
                ["Total Meter", f"{bill['jumlah_meter']} KWH"],
                ["Tarif/kWh", f"Rp {bill['tarifperkwh']:,}".replace(",", ".")],
                ["Total Bayar", f"Rp {bill['total_bayar']:,}".replace(",", ".")],
            ]
            bill_table = Table(bill_data, colWidths=[1.7 * inch, 4.1 * inch])
            bill_table.setStyle(
                TableStyle(
                    [
                        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#6e6258")),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor("#d9d2c9")),
                        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ]
                )
            )
            elements.append(bill_table)
            elements.append(Spacer(1, 0.25 * inch))

            total_box = Table(
                [[Paragraph("TOTAL PEMBAYARAN", style_label), Paragraph(f"Rp {bill['total_bayar']:,}".replace(",", "."), style_value)]],
                colWidths=[3.2 * inch, 2.6 * inch],
            )
            total_box.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e8f1ee")),
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f5b4a")),
                        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            elements.append(total_box)
            elements.append(Spacer(1, 0.2 * inch))

            elements.append(Paragraph("Ini adalah bukti pembayaran resmi. Harap simpan sebagai referensi Anda.", styles["Normal"]))
            elements.append(Paragraph("Terima kasih atas pembayaran Anda.", styles["Normal"]))

            doc.build(elements)
            buffer.seek(0)

            filename = f"bukti_pembayaran_tagihan_{id_tagihan}.pdf"
            return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
        except Exception as e:
            current_app.logger.error(f"Error generating or sending PDF for bill {id_tagihan}: {e}")
            return jsonify({"error": "Terjadi kesalahan saat membuat bukti pembayaran. Silakan coba lagi."}), 500
