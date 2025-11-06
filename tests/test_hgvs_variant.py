import pytest
import requests
from parkinsons_variant_viewer.hgvs_variant import HGVSVariant

# Initialisation tests
def test_initialisation_basic_types():
    var = HGVSVariant("17", 12345, "A", "T")

    # Ensure the first arg is a string called 'chrom'
    assert var.chrom == "17"
    assert isinstance(var.chrom, str)

    # Ensure the second arg is an int called 'pos'
    assert var.pos == 12345
    assert isinstance(var.pos, int)

    # Ensure 3rd & 4th args are 'ref' and 'alt'
    assert var.ref == "A"
    assert var.alt == "T"
    assert var.genome_build == "GRCh38"  # default build

def test_initialisation_with_int_chrom():
    var = HGVSVariant(5, 2222, "G", "C")

    assert var.chrom == "5"  # coerced to str 

def test_initialisation_default_none_attributes():
    var = HGVSVariant("10", 100, "G", "A")

    # Ensure that these attributes are initialised with None 
    assert var.hgvs_genomic is None
    assert var.hgvs_t_and_p is None
    assert var.selected_build is None
    assert var.mane_select_transcript is None

# Create mock_requests_get() pytest fixture for reuse in various tests
@pytest.fixture
def mock_requests_get(monkeypatch):
    """
    Monkeypatch requests.get and allow tests to configure the response 
    JSON, HTTP errors in raise_for_status, and network exceptions 
    raised by requests.get
    """
    captured = {
        "url": None,
        "headers": None,
        "response_json": {},
        "raise_http_error": False,
        "network_exception": None,
    }

    def fake_get(url, headers):
        # If test wants to simulate network-level exception:
        if captured["network_exception"] is not None:
            raise captured["network_exception"]

        captured["url"] = url
        captured["headers"] = headers

        class FakeResponse:
            def raise_for_status(self):
                if captured["raise_http_error"]:
                    raise requests.exceptions.HTTPError("HTTP error")
            def json(self):
                return captured["response_json"]
            status_code = 500 if captured["raise_http_error"] else 200

        return FakeResponse()

    monkeypatch.setattr(
        "parkinsons_variant_viewer.hgvs_variant.requests.get",
        fake_get
    )

    return captured

# Tests for _query_lovd() URL building
def test_query_lovd_default_url(mock_requests_get):
    var = HGVSVariant("17", 12345, "A", "T") # Instantiate variant
    var._query_lovd()  # Trigger fake_get()

    expected = (
        "https://rest.variantvalidator.org/LOVD/lovd/"
        "GRCh38/17:12345:A:T/all/mane/True/True"
        "?content-type=application/json"
    ) 

    # Ensure URL and headers are constructed as expected 
    assert mock_requests_get["url"] == expected
    assert mock_requests_get["headers"] == {"Accept": "application/json"}

def test_query_lovd_with_custom_params(mock_requests_get): 
    var = HGVSVariant(5, 999, "G", "C", genome_build="GRCh37")

    # Use custom parameters to ensure URL still builds properly
    var._query_lovd(
        transcript_model="refseq", 
        select_transcripts="all",
        checkonly="False",
        liftover="primary"
    )

    expected = (
        "https://rest.variantvalidator.org/LOVD/lovd/"
        "GRCh37/5:999:G:C/refseq/all/False/primary"
        "?content-type=application/json"
    )

    # Ensure proper URL with custom parameters 
    assert mock_requests_get["url"] == expected
    

# Tests for HTTP behaviour - responses and errors 
@pytest.fixture
def mock_sleep(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda x: None)

def test_query_lovd_success(mock_requests_get): 
    """ Test a successful HTTP request. """
    mock_requests_get["response_json"] = {"hello": "world"}

    var = HGVSVariant("17", 12345, "A", "T")
    result = var._query_lovd()

    assert result == {"hello": "world"}

def test_query_lovd_http_error(mock_requests_get):
    """ Test that an HTTP error is raised when expected. """
    mock_requests_get["raise_http_error"] = True

    var = HGVSVariant("17", 12345, "A", "T")

    with pytest.raises(requests.exceptions.HTTPError):
        var._query_lovd()

@pytest.mark.parametrize("exception", [
    requests.exceptions.ConnectionError("conn"), 
    requests.exceptions.Timeout("timeout"), 
    requests.exceptions.RequestException("other"),
])

def test_query_lovd_network_errors(mock_requests_get, exception):
    mock_requests_get["network_exception"] = exception

    var = HGVSVariant("17", 12345, "A", "T")

    with pytest.raises(type(exception)):
        var._query_lovd()

def test_query_lovd_calls_sleep(monkeypatch):
    sleep_calls = []

    monkeypatch.setattr("time.sleep", lambda x: sleep_calls.append(x))

    var = HGVSVariant("17", 12345, "A", "T")
    var._query_lovd()

    assert sleep_calls == [0.25]

# Tests for JSON parsing 



# Tests for MANE transcript extraction 


# Tests for get_hgvs()


# Integration testing 


# Testing edge cases 

