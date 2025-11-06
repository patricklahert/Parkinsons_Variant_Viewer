import sqlite3
from pathlib import Path
from parkinsons_variant_viewer.utils.logger import logger


def load_vcf_into_db(vcf_path, db_path):
    """
    Parse a VCF for a single patient and insert variants into the `inputs` table.
    - Patient ID is extracted from filenames like Patient1.vcf
    - Variant numbers start at 1 for each file
    - Existing variants are skipped to avoid duplicates
    """

    stem = Path(vcf_path).stem

    # Only accept files like Patient1.vcf
    if not stem.lower().startswith("patient"):
        logger.warning(f"Skipping non-patient VCF: {vcf_path}")
        return

    # Extract Patient ID
    try:
        patient_id = int(stem.replace("Patient", "").replace("patient", ""))
    except ValueError:
        logger.error(f"Skipping VCF (cannot parse patient ID): {vcf_path}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    logger.info(f"Loading variants for Patient {patient_id} from {vcf_path}")

    with open(vcf_path) as f:
        variant_number = 1
        inserted_count = 0
        skipped_count = 0

        for line in f:
            if line.startswith("#"):
                continue

            chrom, pos, vid, ref, alt, *_ = line.strip().split("\t")

            # Check whether this variant already exists
            exists = cur.execute("""
                SELECT 1 FROM inputs
                WHERE patient_id = ? AND variant_number = ?
            """, (patient_id, variant_number)).fetchone()

            if exists:
                logger.info(
                    f"Skipping duplicate: Patient {patient_id}, Variant {variant_number}"
                )
                skipped_count += 1
                variant_number += 1
                continue

            # Insert new variant
            cur.execute("""
                INSERT INTO inputs
                (patient_id, variant_number, chrom, pos, id, ref, alt)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (patient_id, variant_number, chrom, pos, vid, ref, alt))

            inserted_count += 1
            variant_number += 1

    conn.commit()
    conn.close()

    logger.info(
        f"Finished Patient {patient_id}: {inserted_count} inserted, {skipped_count} skipped."
    )
