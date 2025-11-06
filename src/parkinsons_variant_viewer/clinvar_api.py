import requests
import xmltodict
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

"""Module to interact with ClinVar API and extract variant information. Queries ClinVar with HGVS nomenclature using esearch and returns the ClinVar ID.
Uses the ClinVar ID to query efetch and esummary endpoints to extract detailed variant information."""



class ClinVarApiError(Exception):
    """Custom exception for ClinVar API errors."""
    pass
    

def fetch_clinvar_variant(hgvs):
    """Fetch ClinVar data for HGVS variant."""
    # Search for variant
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    search_params = {"db": "clinvar", "term": f'"{hgvs}"[variant name]', "retmode": "xml"}
    
    try:
        search_resp = requests.get(search_url, params=search_params)
        search_resp.raise_for_status()
        search_data = xmltodict.parse(search_resp.text)
        
        # Get variant IDs
        id_list = search_data.get("eSearchResult", {}).get("IdList", {})
        ids = id_list.get("Id", [])
        if isinstance(ids, str):
            ids = [ids]
        
        if not ids:
            logger.warning(f"No variants found for HGVS: {hgvs}")
            return {"variant": None, "summary": None, "hgvs": hgvs, "found": False}
        
        # Get detailed data
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        
        fetch_params = {"db": "clinvar", "id": ids[0], "rettype": "clinvarset", "retmode": "xml"}
        summary_params = {"db": "clinvar", "id": ids[0], "retmode": "xml"}
        
        fetch_resp = requests.get(fetch_url, params=fetch_params)
        summary_resp = requests.get(summary_url, params=summary_params)
        
        fetch_resp.raise_for_status()
        summary_resp.raise_for_status()
        
        return {
            "variant": xmltodict.parse(fetch_resp.text),
            "summary": xmltodict.parse(summary_resp.text),
            "hgvs": hgvs,
            "found": True,
            "clinvar_id": ids[0]
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching ClinVar data for {hgvs}: {e}")
        raise ClinVarApiError(f"Failed to fetch ClinVar data: {e}")

def get_variant_info(data):
    """Extract variant information from ClinVar data."""
    
    class VariantInfo:
        """Store variant information from ClinVar."""
        def __init__(self, **kwargs):
            self.hgvs = kwargs.get('hgvs')
            self.clinvar_id = kwargs.get('clinvar_id')
            self.chrom = kwargs.get('chrom')
            self.pos = kwargs.get('pos')
            self.variant_id = kwargs.get('variant_id')
            self.ref = kwargs.get('ref')
            self.alt = kwargs.get('alt')
            self.clinical_significance = kwargs.get('clinical_significance')
            self.star_rating = kwargs.get('star_rating')
            self.review_status = kwargs.get('review_status')
            self.conditions_assoc = kwargs.get('conditions_assoc')
            self.transcript = kwargs.get('transcript')
            self.ref_seq_id = kwargs.get('ref_seq_id')
            self.hgnc_id = kwargs.get('hgnc_id')
            self.omim_id = kwargs.get('omim_id')
            self.gene_symbol = kwargs.get('gene_symbol')
            
        def to_dict(self):
            """Convert to dictionary for CSV export."""
            return {
                'CHROM': self.chrom,
                'POS': self.pos,
                'ID': self.variant_id,
                'REF': self.ref,
                'ALT': self.alt,
                'HGVS': self.hgvs,
                'CLINVAR_ID': self.clinvar_id,
                'CLINICAL_SIGNIFICANCE': self.clinical_significance,
                'STAR_RATING': self.star_rating,
                'REVIEW_STATUS': self.review_status,
                'CONDITIONS_ASSOC': self.conditions_assoc,
                'TRANSCRIPT': self.transcript,
                'REF_SEQ_ID': self.ref_seq_id,
                'HGNC_ID': self.hgnc_id,
                'OMIM_ID': self.omim_id,
                'GENE_SYMBOL': self.gene_symbol
            }
    
    if not data.get("found", False):
        return VariantInfo(
            hgvs=data.get("hgvs", ""),
            clinvar_id=data.get("clinvar_id", ""),
            clinical_significance="Not found"
        )
    
    # Get data
    summary = data.get("summary", {}).get("eSummaryResult", {}).get("DocumentSummarySet", {}).get("DocumentSummary", {})
    
    # Default values
    result = {
        'hgvs': data.get("hgvs", ""),
        'clinvar_id': data.get("clinvar_id", ""),
        'variant_id': data.get("clinvar_id", ""),
        'clinical_significance': "Unknown",
        'star_rating': "N/A",
        'review_status': "Unknown",
        'conditions_assoc': "Unknown"
    }
    
    try:
        # Basic info
        result['variant_id'] = summary.get("accession", result['clinvar_id'])
        
        # Extract transcript from title
        title = summary.get("title", "")
        if title:
            match = re.match(r'^([^(]+)', title)
            if match:
                result['transcript'] = match.group(1).strip()
        
        # Clinical significance
        germline = summary.get("germline_classification", {})
        if germline:
            result['clinical_significance'] = germline.get("description", "Unknown")
            result['review_status'] = germline.get("review_status", "Unknown")
            result['star_rating'] = map_review_status_to_stars(result['review_status'])
            
            # Conditions and OMIM
            trait_set = germline.get("trait_set", {})
            if trait_set:
                traits = trait_set.get("trait", [])
                if not isinstance(traits, list):
                    traits = [traits]
                
                conditions = []
                for trait in traits:
                    name = trait.get("trait_name", "")
                    if name:
                        conditions.append(name)
                    
                    # OMIM ID
                    xrefs = trait.get("trait_xrefs", {}).get("trait_xref", [])
                    if not isinstance(xrefs, list):
                        xrefs = [xrefs]
                    
                    for xref in xrefs:
                        if xref.get("db_source") == "OMIM":
                            result['omim_id'] = xref.get("db_id")
                
                if conditions:
                    result['conditions_assoc'] = "; ".join(conditions)
        
        # Genomic coordinates
        var_set = summary.get("variation_set", {}).get("variation", {})
        if var_set:
            # REF/ALT from SPDI
            spdi = var_set.get("canonical_spdi", "")
            if spdi:
                parts = spdi.split(":")
                if len(parts) >= 4:
                    result['ref_seq_id'] = parts[0]
                    result['pos'] = str(int(parts[1]) + 1) if parts[1].isdigit() else parts[1]
                    result['ref'] = parts[2]
                    result['alt'] = parts[3]
            
            # Chromosome
            var_loc = var_set.get("variation_loc", {})
            if var_loc:
                assemblies = var_loc.get("assembly_set", [])
                if not isinstance(assemblies, list):
                    assemblies = [assemblies]
                
                for assembly in assemblies:
                    if assembly.get("status") == "current" or not result.get('chrom'):
                        result['chrom'] = assembly.get("chr", "")
                        if not result.get('pos'):
                            result['pos'] = assembly.get("start", "")
                        break
        
        # Gene info
        genes = summary.get("genes", {}).get("gene", [])
        if not isinstance(genes, list):
            genes = [genes]
        
        for gene in genes:
            if isinstance(gene, dict):
                result['gene_symbol'] = gene.get("symbol", "")
                gene_id = gene.get("GeneID", "")
                if gene_id:
                    result['hgnc_id'] = f"GeneID:{gene_id}"
                break
    
    except Exception as e:
        logger.warning(f"Error extracting variant details: {e}")
    
    return VariantInfo(**result)


def map_review_status_to_stars(status):
    """Map ClinVar review status to star rating."""
    if not status:
        return "0"
    
    status = status.lower()
    if "expert panel" in status:
        return "4"
    elif "multiple submitters" in status and "no conflict" in status:
        return "3"
    elif "multiple submitters" in status:
        return "2"
    elif "single submitter" in status:
        return "1"
    elif "no assertion" in status or "no criteria" in status:
        return "0"
    else:
        return "N/A"


if __name__ == "__main__":
    # Test
    result = fetch_clinvar_variant("NC_000017.11:g.45983420G>T") # Example HGVS - should return data for all fields 
    info = get_variant_info(result)
    
    print("Variant Information:")
    print(f"CHROM: {info.chrom}")
    print(f"POS: {info.pos}")
    print(f"ID: {info.variant_id}")
    print(f"REF: {info.ref}")
    print(f"ALT: {info.alt}")
    print(f"HGVS: {info.hgvs}")
    print(f"CLINVAR_ID: {info.clinvar_id}")
    print(f"CLINICAL_SIGNIFICANCE: {info.clinical_significance}")
    print(f"STAR_RATING: {info.star_rating}")
    print(f"REVIEW_STATUS: {info.review_status}")
    print(f"CONDITIONS_ASSOC: {info.conditions_assoc}")
    print(f"TRANSCRIPT: {info.transcript}")
    print(f"REF_SEQ_ID: {info.ref_seq_id}")
    print(f"HGNC_ID: {info.hgnc_id}")
    print(f"OMIM_ID: {info.omim_id}")
    print(f"GENE_SYMBOL: {info.gene_symbol}")
    
