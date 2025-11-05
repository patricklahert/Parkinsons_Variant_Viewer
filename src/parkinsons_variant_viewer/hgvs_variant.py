# src/parkinsons_variant_viewer/hgvs_variant.py
import requests
import time
from parkinsons_variant_viewer.utils.logger import logger


class HGVSVariant:
    """
    Represents a single genomic variant and fetches HGVS and MANE 
    Select transcript information from the VariantValidator LOVD API.

    Attributes:
        chrom (str): Chromosome identifier (e.g., "17").
        pos (int): 1-based genomic position.
        ref (str): Reference allele.
        alt (str): Alternate allele.
        genome_build (str): Genome assembly ("GRCh38" or "GRCh37").
        hgvs_genomic (str or None): Genomic HGVS notation after fetch.
        hgvs_t_and_p (dict, str, or None): Transcript/protein HGVS info.
        selected_build (str or None): Genome build returned by the API.
        mane_select_transcript (str or None): MANE Select transcript if 
            available.

    Methods:
        fetch(): Queries LOVD API and populates attributes; returns a dict.
        _query_lovd(): Internal helper to query the API and return raw JSON.
        get_hgvs(): Returns the genomic HGVS string for this variant.
    """

    BASE_URL = "https://rest.variantvalidator.org/LOVD/lovd"

    def __init__(self, chrom, pos, ref, alt, genome_build="GRCh38"):
        """
        Initialize a HGVSVariant instance.

        Args:
            chrom (str or int): Chromosome identifier (e.g., "17")
            pos (int): 1-based genomic position
            ref (str): Reference allele
            alt (str): Alternate allele
            genome_build (str, optional): Genome build ("GRCh38" or "GRCh37"). 
                Defaults to "GRCh38".
        """
        self.chrom = str(chrom)
        self.pos = int(pos)
        self.ref = ref
        self.alt = alt
        self.genome_build = genome_build

        # Attributes populated after fetching
        self.hgvs_genomic = None
        self.hgvs_t_and_p = None
        self.selected_build = None
        self.mane_select_transcript = None

        logger.debug(
            f"Initialized HGVSVariant(chrom={chrom}, pos={pos}, "
            f"ref={ref}, alt={alt}, genome_build={genome_build})"
        )

    def _query_lovd(
        self,
        transcript_model="all",
        select_transcripts="mane",
        checkonly="True",
        liftover="True",
    ):
        """
        Internal helper to query the LOVD endpoint of VariantValidator.

        Constructs a pseudo-VCF style variant description from the instance 
        attributes and sends a GET request to the LOVD API to retrieve raw 
        variant information in JSON format.

        Args:
            transcript_model (str, optional): Transcript model to query. Options:
                "refseq", "ensembl", "all". Default is "all".
            select_transcripts (str, optional): Which transcripts to return. Options:
                "select", "mane", "mane_select", "all". Default is "mane".
            checkonly (str, optional): If "True", returns only genomic variant 
                descriptions. Default is "True".
            liftover (str, optional): Lift over setting: "True" (all loci), 
                "primary" (primary assembly only), or "False". Default is "True".

        Returns:
            dict: Raw JSON response from the LOVD API containing variant information.

        Raises:
            requests.exceptions.RequestException: If the API request fails.
        """

        # Build the variant description string (e.g. "17:12345678:G:T")
        variant_desc = f"{self.chrom}:{self.pos}:{self.ref}:{self.alt}"
        url = (
            f"{self.BASE_URL}/{self.genome_build}/{variant_desc}/"
            f"{transcript_model}/{select_transcripts}/{checkonly}/{liftover}"
            "?content-type=application/json"
        )

        # Log the start of query 
        logger.info("Querying LOVD API for variant: %s", variant_desc)
        logger.debug("Request URL: %s", url)

        try: 
            response = requests.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            logger.info(
                "Received successful response for variant: %s (status %s)",
                variant_desc,
                response.status_code,
            )
        except requests.exceptions.RequestException as e:
            logger.error(
                "Request failed for variant %s: %s",
                variant_desc,
                e,
                exc_info=True,
            )
            raise
        
        # Respect delay between API calls requirements
        time.sleep(0.25)  

        logger.debug("Returning JSON response for variant: %s", variant_desc)

        return response.json()

    def fetch(self):
        """
        Fetch HGVS nomenclature and transcript information for this variant from
        the LOVD endpoint.

        Uses the internal `_query_lovd` helper to retrieve variant data, then
        parses the JSON response to populate instance attributes and extract
        relevant HGVS and transcript information.

        Attributes Populated:
            hgvs_genomic (str or None): Genomic HGVS notation 
                (e.g., NC_000017.11:g.45983420G>T).
            hgvs_t_and_p (dict, str, or None): Transcript and protein-level 
                HGVS information.
            selected_build (str or None): Genome build returned by the API 
                (e.g., "GRCh38").
            mane_select_transcript (str or None): MANE Select transcript ID if 
                available (e.g., "NM_000088.3").

        Returns:
            dict: Contains the following keys:
                - "variant_description" (str): Colon-separated pseudo-VCF
                description of the variant.
                - "hgvs_genomic" (str or None): Genomic HGVS notation.
                - "hgvs_t_and_p" (dict, str, or None): Transcript and protein-level
                HGVS info.
                - "selected_build" (str or None): Genome build used.
                - "mane_select_transcript" (str or None): Extracted MANE Select
                transcript if present.

        Notes:
            - If no valid variant data is found in the LOVD response, the
            function returns None.
            - MANE Select transcript extraction is attempted from either the
            "hgvs_t_and_p" dict or by pattern matching NM_ identifiers in a
            string fallback.
            - This method may raise `requests.exceptions.RequestException`
            indirectly via `_query_lovd` if the API request fails.
        """

        data = self._query_lovd()

        ## Extract HGVS, notation, transcript & protein level info, and build
        # Filter top-level keys to find the variant keys (ignore metadata)
        variant_keys = [k for k in data.keys() if ":" in k and k != "metadata"]

        # If no variant keys found, return None
        if not variant_keys:
            return None

        # Take the first variant key as this is the variant of interest
        variant_key = variant_keys[0]

        # Get the dictionary containing the variant information
        # LOVD nests the variant under another layer using the same key
        variant_dict = data[variant_key].get(variant_key)
        if not variant_dict:
            # If the nested dictionary is missing, return None
            return None

        # 'variant_dict' now contains the actual data we want:
        # g_hgvs, hgvs_t_and_p, selected_build, etc.
        info = variant_dict

        # Populate attributes
        self.hgvs_genomic = info.get("g_hgvs")
        self.hgvs_t_and_p = info.get("hgvs_t_and_p")
        self.selected_build = info.get("selected_build")

        ## Extract the MANE Select transcript, if present 
        # Initialize variable to store MANE Select transcript
        mane_transcript = None

        # Case 1: hgvs_t_and_p is a dictionary (common structured response)
        # Sometimes the API returns the MANE Select transcript under the key "mane_select"
        if isinstance(self.hgvs_t_and_p, dict):
            mane_transcript = self.hgvs_t_and_p.get("mane_select")

        # Case 2: hgvs_t_and_p is a string (less structured fallback)
        # Sometimes the API returns a simple string with transcript info embedded
        elif isinstance(self.hgvs_t_and_p, str):
            # Use regex to search for a RefSeq transcript pattern (e.g., NM_000093.4)
            import re
            match = re.search(r"(NM_\d+\.\d+)", self.hgvs_t_and_p)
            if match:
                # Extract the first matching transcript
                mane_transcript = match.group(1)

        # Finally, assign the extracted MANE Select transcript to the class attribute
        self.mane_select_transcript = mane_transcript

        return {
            "variant_description": f"{self.chrom}:{self.pos}:{self.ref}:{self.alt}",
            "hgvs_genomic": self.hgvs_genomic,
            "hgvs_t_and_p": self.hgvs_t_and_p,
            "selected_build": self.selected_build,
            "mane_select_transcript": self.mane_select_transcript,
        }

    def get_hgvs(self):
        """
        Return the genomic HGVS string for this variant.

        If the HGVS information has not been fetched yet, this method will
        call `fetch()` to query the LOVD API and populate the attribute.

        Returns:
            str or None: The genomic HGVS notation (e.g., 
            "NC_000017.11:g.45983420G>T"). Returns None if fetching fails.
        """
        if not self.hgvs_genomic:
            self.fetch()
        return self.hgvs_genomic


if __name__ == "__main__":
    var = HGVSVariant("17", 45983420, "G", "T")
    print(var.fetch())
    print(var.get_hgvs())
