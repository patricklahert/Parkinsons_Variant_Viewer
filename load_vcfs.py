import os
from src.parkinsons_variant_viewer.web import create_app
from src.parkinsons_variant_viewer.web.db import get_db_path
from src.parkinsons_variant_viewer.web.loaders.vcf_loader import load_vcf_into_db

# Create the Flask app context so get_db_path works
app = create_app()

VCF_DIR = "data/input/"   # directory containing your Patient*.vcf files

with app.app_context():
    db_path = get_db_path()
    print(f"Using database: {db_path}")

    # Loop through every .vcf file in the input directory
    for filename in os.listdir(VCF_DIR):
        if filename.lower().endswith(".vcf"):
            vcf_path = os.path.join(VCF_DIR, filename)
            print(f"Loading: {vcf_path}")

            # Call your loader
            load_vcf_into_db(vcf_path, db_path)

    print("All VCFs loaded into the database.")
