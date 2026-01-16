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
    get_admin_stats,
    get_bill,
    get_usage,
    list_bills,
    list_customers,
    list_tariffs,
    list_usages,
    update_bill_status,
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


def register_routes(app: Flask) -> None:
    @app.route("/")
    def index():
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            role = request.form.get("role", "pelanggan")
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            conn = get_db()
            user = None
            if role == "admin":
                user = login_admin(conn, username, password)
                if user:
                    session.clear()
                    session["user_id"] = int(user["id_user"])
                    session["username"] = user["username"]
                    session["name"] = user["nama_admin"]
                    session["role"] = "admin"
            else:
                user = login_pelanggan(conn, username, password)
                if user:
                    session.clear()
                    session["user_id"] = int(user["id_pelanggan"])
                    session["username"] = user["username"]
                    session["name"] = user["nama_pelanggan"]
                    session["role"] = "pelanggan"

            if user:
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
        usages = list_usages(conn)
        return render_template("admin/usage_list.html", usages=usages)

    @app.route("/admin/customers")
    @login_required("admin")
    def admin_customers():
        conn = get_db()
        customers = list_customers(conn)
        return render_template("admin/customers.html", customers=customers)

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
        status_filter = None
        if status == "unpaid":
            status_filter = "BELUM BAYAR"
        elif status == "paid":
            status_filter = "SUDAH BAYAR"
        bills = list_bills(conn, status=status_filter)
        return render_template(
            "admin/bills.html",
            bills=bills,
            status=status,
        )

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
        update_bill_status(conn, id_tagihan, "SUDAH BAYAR")
        flash("Tagihan ditandai lunas.", "success")
        return redirect(url_for("admin_bills"))

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
            update_bill_status(conn, id_tagihan, "SUDAH BAYAR")

        return jsonify({"status": "ok"})
