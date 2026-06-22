import logging
import hashlib
import csv
from io import BytesIO, StringIO
from datetime import datetime
from flask import Blueprint, render_template, request, send_file, session, redirect, url_for
from fpdf import FPDF
from db import get_user_id, get_history, get_versions, get_all_notes, save_entry, load_entry
from bio_engine import run_analysis
from i18n import i18n

analysis_bp = Blueprint('analysis', __name__)


@analysis_bp.route("/app", methods=["GET", "POST"])
def index():
    if not get_user_id():
        return redirect(url_for('auth.login'))
    user_id = get_user_id()

    results = None
    seq = ""
    pdb_id = ""
    notes = ""
    entry_id = None
    versions = []
    version_group = None

    load_id = request.args.get("load_id")
    if load_id:
        row = load_entry(load_id, user_id)
        if row:
            seq = row[0]
            pdb_id = row[1] if row[1] != "N/A" else ""
            notes = row[2] or ""
            entry_id = int(load_id)
            results = run_analysis(seq, pdb_id=pdb_id)

    if request.method == "POST":
        seq = request.form.get("sequence", "")
        pdb_id = request.form.get("pdb_id", "").strip().lower()
        if seq:
            results = run_analysis(seq, pdb_id=pdb_id)

        if results and "error" not in results:
            try:
                entry_id, vg = save_entry(user_id, seq, pdb_id, results)
                version_group = vg
                versions = get_versions(user_id, vg)
            except Exception as e:
                logging.error(i18n.translate("database_save_error", error=e))

    if entry_id and results and "error" not in results:
        if not version_group:
            vg = hashlib.md5(seq.encode()).hexdigest()[:12]
            version_group = vg
            versions = get_versions(user_id, vg)

    if results and "error" not in results:
        results['strategy_text'] = i18n.translate(results['strategy'])
        results['charge_info_text'] = i18n.translate(results['charge_info'], pi=results['pi'])
        results['stability_info_text'] = i18n.translate(results['stability_info_key'], index=round(results['instability'], 2))

    js_trans = i18n.get_js_translations()

    return render_template("index.html",
                           results=results,
                           sequence=seq,
                           pdb_id=pdb_id,
                           entry_id=entry_id,
                           history=get_history(user_id),
                           username=session.get('username'),
                           notes=notes,
                           all_notes=get_all_notes(user_id),
                           versions=versions,
                           version_group=version_group,
                           js_translations=js_trans,
                           current_lang=session.get('lang', 'en'))


@analysis_bp.route("/download_pdf", methods=["POST"])
def download_pdf():
    if not get_user_id():
        return redirect(url_for('auth.login'))
    seq = request.form.get("sequence", "")
    pdb_id = request.form.get("pdb_id", "").strip().lower()
    notes = request.form.get("notes", "")
    if not seq:
        return i18n.translate("missing_sequence"), 400
    results = run_analysis(seq, pdb_id=pdb_id)
    if "error" in results:
        return i18n.translate("analysis_error"), 400

    pdf = FPDF()
    pdf.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", uni=True)
    pdf.add_font("DejaVu", "B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", uni=True)
    pdf.add_page()

    w = pdf.w - 2 * pdf.l_margin

    pdf.set_fill_color(6, 9, 19)
    pdf.rect(0, 0, pdf.w, 35, "F")
    pdf.set_y(10)
    pdf.set_font("DejaVu", "B", 18)
    pdf.set_text_color(6, 182, 212)
    pdf.cell(w, 8, i18n.translate("prism_pdf_title"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(w, 5, i18n.translate("pdf_subtitle"), align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf.set_draw_color(34, 47, 84)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + w, pdf.get_y())
    pdf.ln(8)

    pdb_label = pdb_id.upper() if pdb_id else i18n.translate("na")
    pdf.set_font("DejaVu", "B", 13)
    pdf.set_text_color(241, 245, 249)
    pdf.cell(w, 7, i18n.translate("pdf_pdb_id", id=pdb_label), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)

    def meta_row(label, value, alt=False):
        if alt:
            pdf.set_fill_color(15, 20, 36)
        else:
            pdf.set_fill_color(11, 14, 25)
        pdf.set_font("DejaVu", "", 10)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(w * 0.4, 7, f"  {label}", new_x="RIGHT", new_y="TOP")
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(241, 245, 249)
        pdf.cell(w * 0.6, 7, f"{value}", new_x="LMARGIN", new_y="NEXT")

    meta = [
        (i18n.translate("pdf_seq_length"), f"{results['length']} aa"),
        (i18n.translate("pdf_mol_weight"), f"{results['weight']} Da"),
        (i18n.translate("pdf_isoelectric_point"), f"{results['pi']}"),
        (i18n.translate("pdf_gravy"), f"{results['gravy']}"),
        (i18n.translate("pdf_aromaticity"), f"{results['aromaticity']}%"),
        (i18n.translate("pdf_instability"), f"{results['instability']}"),
        (i18n.translate("pdf_stability"), results['stability_status']),
    ]
    for i, (k, v) in enumerate(meta):
        meta_row(k, v, alt=(i % 2 == 0))

    pdf.ln(6)
    pdf.set_draw_color(34, 47, 84)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + w, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(6, 182, 212)
    pdf.cell(w, 6, i18n.translate("pdf_secondary_structure"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    ss_rows = [
        (i18n.translate("pdf_alpha_helix"), f"{results['helix']}%"),
        (i18n.translate("pdf_beta_sheet"), f"{results['sheet']}%"),
        (i18n.translate("pdf_loop_turn"), f"{results['turn']}%"),
    ]
    for i, (k, v) in enumerate(ss_rows):
        meta_row(k, v, alt=(i % 2 == 0))

    pdf.ln(6)
    pdf.set_draw_color(34, 47, 84)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + w, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(6, 182, 212)
    pdf.cell(w, 6, i18n.translate("pdf_spectroscopic_data"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    spec_rows = [
        (i18n.translate("pdf_cys_reduced"), f"{results['ext_reduced']} M-1cm-1"),
        (i18n.translate("pdf_cys_oxidized"), f"{results['ext_oxidized']} M-1cm-1"),
    ]
    for i, (k, v) in enumerate(spec_rows):
        meta_row(k, v, alt=(i % 2 == 0))

    pdf.ln(6)
    pdf.set_draw_color(34, 47, 84)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + w, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(6, 182, 212)
    pdf.cell(w, 6, i18n.translate("pdf_aa_distribution"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    for group_name, residues in results['aa_groups'].items():
        top = sorted(residues, key=lambda r: r['pct'], reverse=True)[:3]
        top_str = ", ".join(f"{r['c3']} ({r['pct']}%)" for r in top)
        top_total = sum(r['pct'] for r in top)
        row_label = i18n.translate(group_name)[:35]
        row_value = f"{top_str}  | {i18n.translate('pdf_total')} {round(top_total, 2)}%"
        pdf.set_fill_color(15, 20, 36)
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(w * 0.35, 6, f"  {row_label}", new_x="RIGHT", new_y="TOP")
        pdf.set_font("DejaVu", "", 8)
        pdf.set_text_color(241, 245, 249)
        pdf.cell(w * 0.65, 6, row_value, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.set_draw_color(34, 47, 84)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + w, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("DejaVu", "B", 11)
    pdf.set_text_color(6, 182, 212)
    pdf.cell(w, 6, i18n.translate("pdf_drug_strategy"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("DejaVu", "", 9)
    pdf.set_text_color(203, 213, 225)
    pdf.multi_cell(w, 5, i18n.translate(results['strategy']))

    pdf.ln(4)
    if notes:
        pdf.ln(8)
        pdf.set_draw_color(34, 47, 84)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + w, pdf.get_y())
        pdf.ln(6)
        pdf.set_font("DejaVu", "B", 11)
        pdf.set_text_color(6, 182, 212)
        pdf.cell(w, 6, i18n.translate("pdf_lab_notes"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        pdf.set_font("DejaVu", "", 9)
        pdf.set_text_color(203, 213, 225)
        pdf.multi_cell(w, 5, notes)

    pdf.ln(4)
    pdf.set_font("DejaVu", "", 7)
    pdf.set_text_color(100, 116, 139)
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    pdf.cell(w, 4, i18n.translate("pdf_generated", date=now, pdb=pdb_label), align="C", new_x="LMARGIN", new_y="NEXT")

    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=f"PRISM_report_{pdb_label}.pdf")


@analysis_bp.route("/download_csv", methods=["POST"])
def download_csv():
    if not get_user_id():
        return redirect(url_for('auth.login'))
    seq = request.form.get("sequence", "")
    pdb_id = request.form.get("pdb_id", "").strip().lower()
    if not seq:
        return i18n.translate("missing_sequence"), 400
    results = run_analysis(seq, pdb_id=pdb_id)
    if "error" in results:
        return i18n.translate("analysis_error"), 400

    pdb_label = pdb_id.upper() if pdb_id else i18n.translate("na")

    buf = StringIO()
    w = csv.writer(buf)

    w.writerow([i18n.translate("csv_header")])
    w.writerow([i18n.translate("csv_pdb_id"), pdb_label])
    w.writerow([i18n.translate("csv_date"), datetime.now().strftime("%Y-%m-%d %H:%M")])
    w.writerow([])

    w.writerow([i18n.translate("csv_basic_metrics")])
    w.writerow([i18n.translate("csv_seq_length"), results['length']])
    w.writerow([i18n.translate("csv_mol_weight"), results['weight']])
    w.writerow([i18n.translate("csv_isoelectric_point"), results['pi']])
    w.writerow([i18n.translate("csv_gravy"), results['gravy']])
    w.writerow([i18n.translate("csv_aromaticity"), results['aromaticity']])
    w.writerow([i18n.translate("csv_instability"), results['instability']])
    w.writerow([i18n.translate("csv_stability"), results['stability_status']])
    w.writerow([])

    w.writerow([i18n.translate("csv_secondary_structure")])
    w.writerow([i18n.translate("csv_alpha_helix"), results['helix']])
    w.writerow([i18n.translate("csv_beta_sheet"), results['sheet']])
    w.writerow([i18n.translate("csv_loop_turn"), results['turn']])
    w.writerow([])

    w.writerow([i18n.translate("csv_spectroscopic_data")])
    w.writerow([i18n.translate("pdf_cys_reduced"), results['ext_reduced']])
    w.writerow([i18n.translate("pdf_cys_oxidized"), results['ext_oxidized']])
    w.writerow([])

    w.writerow([i18n.translate("csv_aa_distribution")])
    header = [i18n.translate("csv_group"), i18n.translate("csv_amino_acid"), i18n.translate("csv_code"), i18n.translate("csv_percentage")]
    w.writerow(header)
    for group_name, residues in results['aa_groups'].items():
        for aa in residues:
            w.writerow([i18n.translate(group_name), aa['c3'], aa['c1'], aa['pct']])
    w.writerow([])

    w.writerow([i18n.translate("csv_drug_strategy")])
    w.writerow([i18n.translate(results['strategy'])])
    w.writerow([])
    w.writerow([i18n.translate("csv_electrostatic")])
    w.writerow([i18n.translate(results['charge_info'], pi=results['pi'])])
    w.writerow([])
    w.writerow([i18n.translate("csv_stability_info")])
    w.writerow([i18n.translate(results['stability_info_key'], index=round(results['instability'], 2))])

    csv_bytes = buf.getvalue().encode('utf-8-sig')
    return send_file(BytesIO(csv_bytes), mimetype="text/csv", as_attachment=True, download_name=f"PRISM_data_{pdb_label}.csv")
