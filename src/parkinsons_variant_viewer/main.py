# src/parkinsons_variant_viewer/main.py
import csv
from parkinsons_variant_viewer.hgvs_variant import HGVSVariant
from parkinsons_variant_viewer.clinvar_api import fetch_clinvar_variant, get_variant_info

INPUT_VCF = "data/input/Patient3.vcf"  # replace with desired VCF 
OUTPUT_CSV = "data/output/Patient3_variant_clinvar_summary.csv"


def read_pseudo_vcf(vcf_file):
    """
    Reads a pseudo-VCF with columns: CHROM, POS, REF, ALT
    Returns a list of dicts: [{"chrom": ..., "pos": ..., "ref": ..., "alt": ...}, ...]
    """
    variants = []
    with open(vcf_file, "r") as f:
        for line in f:
            if line.startswith("#"):
                continue
            chrom, pos, _, ref, alt = line.strip().split("\t")
            variants.append({
                "chrom": chrom,
                "pos": int(pos),
                "ref": ref,
                "alt": alt
            })
    return variants


def main():
    variants = read_pseudo_vcf(INPUT_VCF)
    output_rows = []

    for var in variants:
        print(f"\nProcessing variant: {var['chrom']}:{var['pos']} {var['ref']}->{var['alt']}")
        
        # Step 1: Get HGVS name
        hgvs_variant = HGVSVariant(var["chrom"], var["pos"], var["ref"], var["alt"])
        hgvs_id = hgvs_variant.get_hgvs()
        print(f"HGVS: {hgvs_id}")

        # Step 2: Fetch ClinVar information
        clinvar_data = fetch_clinvar_variant(hgvs_id)
        variant_info = get_variant_info(clinvar_data)

        # Step 3: Add to output
        output_rows.append({
            "chrom": var["chrom"],
            "pos": var["pos"],
            "ref": var["ref"],
            "alt": var["alt"],
            "hgvs": variant_info.hgvs,
            "clinvar_id": variant_info.clinvar_id,
            "clinical_significance": variant_info.clinical_significance,
            "star_rating": variant_info.star_rating,
            "review_status": variant_info.review_status
        })

        # Print summary
        print(f"ClinVar ID: {variant_info.clinvar_id}")
        print(f"Clinical Significance: {variant_info.clinical_significance}")
        print(f"Star Rating: {variant_info.star_rating}")
        print(f"Review Status: {variant_info.review_status}")

    # Step 4: Write to CSV
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_rows[0].keys())
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"\n Finished! Results saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
