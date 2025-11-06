PRAGMA foreign_keys = ON; 

-- Drop old tables if they exist 
DROP TABLE IF EXISTS outputs; 
DROP TABLE IF EXISTS inputs; 

-- Input table: raw variant data 
CREATE TABLE inputs (
    patient_id INTEGER NOT NULL, 
    variant_number INTEGER NOT NULL, 
    chrom TEXT NOT NULL, 
    pos INTEGER NOT NULL, 
    id TEXT, 
    ref TEXT NOT NULL, 
    alt TEXT NOT NULL, 
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
    PRIMARY KEY (patient_id, variant_number)
);

-- Output table: derived annotations 
CREATE TABLE outputs(
    patient_id INTEGER NOT NULL,
    variant_number INTEGER NOT NULL, 
    hgvs TEXT, 
    clinvar_id TEXT,
    clinical_significance TEXT,
    star_rating INTEGER,
    review_status TEXT,
    conditions_assoc TEXT,
    transcript TEXT,
    ref_seq_id TEXT, 
    hgnc_id TEXT,
    omim_id TEXT,
    g_change TEXT,
    c_change TEXT,
    p_change TEXT,
    analysed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
    PRIMARY KEY (patient_id, variant_number),
    FOREIGN KEY (patient_id, variant_number)
        REFERENCES inputs (patient_id, variant_number)
        ON DELETE CASCADE
);