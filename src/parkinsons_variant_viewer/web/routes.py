from flask import Blueprint, render_template, request, redirect, url_for
from .db import get_db

bp = Blueprint("web", __name__)


# Home page: list all variants (input + output if present)
@bp.route("/")
def index():
    db = get_db()

    # Join the inputs and outputs tables on the composite key
    rows = db.execute("""
        SELECT 
            i.patient_id,
            i.variant_number,
            i.chrom,
            i.pos,
            i.id,
            i.ref,
            i.alt,
            o.hgvs,
            o.clinvar_id,
            o.clinical_significance,
            o.star_rating,
            o.review_status,
            o.conditions_assoc,
            o.transcript,
            o.ref_seq_id,
            o.hgnc_id,
            o.omim_id,
            o.g_change,
            o.c_change,
            o.p_change
        FROM inputs AS i
        LEFT JOIN outputs AS o
        ON i.patient_id = o.patient_id
           AND i.variant_number = o.variant_number
        ORDER BY i.patient_id, i.variant_number
    """).fetchall()

    return render_template("variants.html", variants=rows)


# Add a new *input* variant manually
@bp.route("/add", methods=["GET", "POST"])
def add_variant():
    db = get_db()

    if request.method == "POST":
        patient_id = request.form["patient_id"]
        variant_number = request.form["variant_number"]
        chrom = request.form["chrom"]
        pos = request.form["pos"]
        vid = request.form["id"]
        ref = request.form["ref"]
        alt = request.form["alt"]

        db.execute(
            """
            INSERT INTO inputs 
            (patient_id, variant_number, chrom, pos, id, ref, alt)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (patient_id, variant_number, chrom, pos, vid, ref, alt),
        )

        db.commit()
        return redirect(url_for("web.index"))

    return render_template("add_variant.html")

# Route to view the table of input data 
@bp.route("/inputs")
def view_inputs():
    db = get_db()

    rows = db.execute("""
        SELECT patient_id, variant_number, chrom, pos, id, ref, alt
        FROM inputs
        ORDER BY patient_id, variant_number
    """).fetchall()

    return render_template("inputs.html", inputs=rows)