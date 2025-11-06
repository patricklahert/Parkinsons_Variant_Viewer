import sqlite3
from parkinsons_variant_viewer.web.loaders.vcf_loader import load_vcf_into_db


def create_test_db(path):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE inputs (
            patient_id INTEGER,
            variant_number INTEGER,
            chrom TEXT,
            pos TEXT,
            id TEXT,
            ref TEXT,
            alt TEXT
        )
    """)
    conn.commit()
    conn.close()

# Test variants are loaded for a valid patient file 
def test_loads_variants(tmp_path):
    # Setup
    db_path = tmp_path / "test.db"
    create_test_db(db_path)

    vcf = tmp_path / "Patient1.vcf"
    vcf.write_text(
        """##fileformat=VCFv4.2
#CHROM POS ID REF ALT QUAL FILTER INFO
1\t1000\trs1\tA\tG
1\t2000\trs2\tT\tC
"""
    )

    # Execute
    load_vcf_into_db(vcf, db_path)

    # Verify
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM inputs ORDER BY variant_number").fetchall()

    assert len(rows) == 2
    assert rows[0][0] == 1         # patient_id
    assert rows[0][1] == 1         # variant_number
    assert rows[0][2:] == ("1", "1000", "rs1", "A", "G")

    conn.close()

# Test that duplicates will be skipped based on patient ID + variant ID 
def test_skips_duplicate_variants(tmp_path):
    db_path = tmp_path / "test.db"
    create_test_db(db_path)

    vcf = tmp_path / "Patient3.vcf"
    vcf.write_text(
        "1\t1000\trs1\tA\tG\n"
        "1\t2000\trs2\tT\tC\n"
    )

    # Load once
    load_vcf_into_db(vcf, db_path)

    # Load again → should skip both
    load_vcf_into_db(vcf, db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM inputs").fetchall()

    # Still only 2 rows
    assert len(rows) == 2

    conn.close()

# Test that vcfs not containing Patient in name will be skipped
def test_skips_non_patient_vcf(tmp_path):
    db_path = tmp_path / "test.db"
    create_test_db(db_path)

    vcf = tmp_path / "random.vcf"
    vcf.write_text("1\t1000\trs1\tA\tG\n")

    load_vcf_into_db(vcf, db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM inputs").fetchall()
    assert rows == []  # no inserts

    conn.close()

# Test that vcfs not containing a patient number in filename will be skipped
def test_skips_non_patient_vcf(tmp_path):
    db_path = tmp_path / "test.db"
    create_test_db(db_path)

    vcf = tmp_path / "random.vcf"
    vcf.write_text("1\t1000\trs1\tA\tG\n")

    load_vcf_into_db(vcf, db_path)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM inputs").fetchall()
    assert rows == []  # no inserts

    conn.close()

# Test that variant numbering restarts per file 
def test_variant_numbers_reset_per_patient(tmp_path):
    db_path = tmp_path / "test.db"
    create_test_db(db_path)

    v1 = tmp_path / "Patient7.vcf"
    v2 = tmp_path / "Patient7_repeat.vcf"  # gets skipped entirely (invalid name)
    v1.write_text("1\t100\trs1\tA\tG\n1\t200\trs2\tA\tT\n")
    v2.write_text("1\t300\trs3\tC\tG\n")

    load_vcf_into_db(v1, db_path)
    load_vcf_into_db(v2, db_path)

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT variant_number FROM inputs ORDER BY variant_number").fetchall()

    assert rows == [(1,), (2,)]  # variants from 2nd file should not be added
