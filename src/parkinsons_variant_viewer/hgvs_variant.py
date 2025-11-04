# src/parkinsons_variant_viewer/hgvs_variant.py
import requests
import time


class HGVSVariant:
    """Fetches HGVS and MANE select transcript info from the VariantValidator LOVD API."""

    BASE_URL = "https://rest.variantvalidator.org/LOVD/lovd"

    def __init__(self, chrom, pos, ref, alt, genome_build="GRCh38"):
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

    def _query_lovd(
        self,
        transcript_model="all",
        select_transcripts="mane",
        checkonly="True",
        liftover="True",
    ):
        """
        Internal helper to query the LOVD API and return raw JSON.
        """
        variant_desc = f"{self.chrom}:{self.pos}:{self.ref}:{self.alt}"
        url = (
            f"{self.BASE_URL}/{self.genome_build}/{variant_desc}/"
            f"{transcript_model}/{select_transcripts}/{checkonly}/{liftover}"
            "?content-type=application/json"
        )

        response = requests.get(url, headers={"Accept": "application/json"})
        response.raise_for_status()
        time.sleep(0.25)  # rate limit safety
        return response.json()

    def fetch(self):
        """
        Fetch HGVS and transcript information from the LOVD endpoint.
        """
        data = self._query_lovd()

        # Identify correct nested keys
        variant_keys = [k for k in data.keys() if ":" in k and k != "metadata"]
        if not variant_keys:
            return None
        outer = variant_keys[0]
        inner = next(iter(data[outer].keys()))
        info = data[outer][inner]

        # Populate attributes
        self.hgvs_genomic = info.get("g_hgvs")
        self.hgvs_t_and_p = info.get("hgvs_t_and_p")
        self.selected_build = info.get("selected_build")

        # Try to extract MANE Select transcript if present
        # Sometimes this appears under hgvs_t_and_p or a separate "mane_select" field
        mane_transcript = None
        if isinstance(self.hgvs_t_and_p, dict):
            mane_transcript = self.hgvs_t_and_p.get("mane_select")
        elif isinstance(self.hgvs_t_and_p, str):
            # crude fallback: detect NM_... pattern in string if present
            import re
            match = re.search(r"(NM_\d+\.\d+)", self.hgvs_t_and_p)
            if match:
                mane_transcript = match.group(1)

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
        Returns only the HGVS genomic name as a string (fetching it if not already cached).
        """
        if not self.hgvs_genomic:
            self.fetch()
        return self.hgvs_genomic


if __name__ == "__main__":
    var = HGVSVariant("17", 45983420, "G", "T")
    print(var.fetch())
    print(var.get_hgvs())
