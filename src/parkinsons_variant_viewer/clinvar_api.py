import requests
import xmltodict
import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClinVarApiError(Exception):
    """
    Custom exception raised when there's an error with ClinVar API calls.
    """
    pass
    

class VariantInfo:
    """
    Class to store extracted variant information from ClinVar data.
    """
    def __init__(self, hgvs, clinvar_id, consensus_sequence=None, star_rating=None, 
                 clinical_significance=None, review_status=None):
        self.hgvs = hgvs
        self.clinvar_id = clinvar_id
        self.consensus_sequence = consensus_sequence
        self.star_rating = star_rating
        self.clinical_significance = clinical_significance
        self.review_status = review_status
    

def fetch_clinvar_variant(hgvs_expression):
    """ takes a variant in HGVS nomenclature and returns ClinVar data as a dict"""

    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    search_params = {
        "db": "clinvar",
        "term": f'"{hgvs_expression}"[variant name]',
        "retmode": "xml"
    }
    
    try:
        # Search for the specific HGVS variant
        search_response = requests.get(search_url, params=search_params)
        search_response.raise_for_status()
        
        # Parse XML search response
        search_data = xmltodict.parse(search_response.text)
        
        # Extract ID list from XML
        id_list = search_data.get("eSearchResult", {}).get("IdList", {})
        variant_ids = []
        if id_list and id_list.get("Id"):
            variant_ids = id_list["Id"]
            if isinstance(variant_ids, str):
                variant_ids = [variant_ids]
        
        if not variant_ids:
            logger.warning(f"No variants found for HGVS: {hgvs_expression}")
            return {"variant": None, "hgvs": hgvs_expression, "found": False}
        
        # Try esummary instead of efetch for better results
        summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        summary_params = {
            "db": "clinvar",
            "id": variant_ids[0],
            "retmode": "xml"
        }
        
        summary_response = requests.get(summary_url, params=summary_params)
        summary_response.raise_for_status()
    
        # Parse XML response to dictionary
        variant_data = xmltodict.parse(summary_response.text)
        return {
            "variant": variant_data,
            "hgvs": hgvs_expression,
            "found": True,
            "clinvar_id": variant_ids[0]
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching ClinVar data for HGVS {hgvs_expression}: {e}")
        raise ClinVarApiError(f"Failed to fetch ClinVar data: {e}")

def get_variant_info(variant_data):
    """
    Extract information from ClinVar variant data and return a VariantInfo object

    Returns:
        VariantInfo: Object containing extracted variant information
    """
    if not variant_data.get("found", False):
        return VariantInfo(
            hgvs=variant_data.get("hgvs", ""),
            clinvar_id=variant_data.get("clinvar_id", ""),
            consensus_sequence="Not found",
            star_rating="N/A"
        )
    
    hgvs = variant_data.get("hgvs", "")
    clinvar_id = variant_data.get("clinvar_id", "")
    xml_data = variant_data.get("variant", {})
    
    # Initialize default values
    consensus_sequence = "Unknown"
    star_rating = "N/A"
    clinical_significance = "Unknown"
    review_status = "Unknown"
    
    try:
        # Navigate through the XML structure: eSummaryResult -> DocumentSummarySet -> DocumentSummary
        doc_summary_set = xml_data.get("eSummaryResult", {}).get("DocumentSummarySet", {})
        doc_summary = doc_summary_set.get("DocumentSummary", {})
        
        # Extract clinical significance from germline_classification
        germline_class = doc_summary.get("germline_classification", {})
        if germline_class:
            consensus_sequence = germline_class.get("description", "Unknown")
            clinical_significance = consensus_sequence
            review_status = germline_class.get("review_status", "Unknown")
            star_rating = map_review_status_to_stars(review_status)
    
    except Exception as e:
        logger.warning(f"Error extracting variant details: {e}")
    
    return VariantInfo(
        hgvs=hgvs,
        clinvar_id=clinvar_id,
        consensus_sequence=consensus_sequence,
        star_rating=star_rating,
        clinical_significance=clinical_significance,
        review_status=review_status
    )


def map_review_status_to_stars(review_status):
    """
    Map ClinVar review status to star rating system.
    
    ClinVar star rating system:
    - 4 stars: reviewed by expert panel
    - 3 stars: reviewed by multiple submitters, no conflicts
    - 2 stars: reviewed by multiple submitters, conflicts resolved
    - 1 star: reviewed by single submitter
    - 0 stars: no assertion criteria provided
    """
    if not review_status:
        return "0"
    
    review_status_lower = review_status.lower()
    
    if "expert panel" in review_status_lower:
        return "4"
    elif "multiple submitters" in review_status_lower and "no conflict" in review_status_lower:
        return "3"
    elif "multiple submitters" in review_status_lower:
        return "2"
    elif "single submitter" in review_status_lower:
        return "1"
    elif "no assertion" in review_status_lower or "no criteria" in review_status_lower:
        return "0"
    else:
        return "N/A"




if __name__ == "__main__":
    # Test with a complete HGVS expression
    result = fetch_clinvar_variant("NC_000017.11:g.45983420G>T") 
    
    # Extract information using get_variant_info function
    variant_info = get_variant_info(result)
    
    print("Variant Information:")
    print(f"HGVS: {variant_info.hgvs}")
    print(f"ClinVar ID: {variant_info.clinvar_id}")
    print(f"Clinical Significance: {variant_info.clinical_significance}")
    print(f"Star Rating: {variant_info.star_rating}")
    print(f"Review Status: {variant_info.review_status}")
    
