from typing import Optional, List, Dict, Any
import json
import time
from collections import deque
import requests
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("clinicaltrials-mcp-server", version="1.0.0")

# Base URL for Clinical Trials API
# Base URL for Clinical Trials API
# Documentation: https://clinicaltrials.gov/data-api/api
API_BASE_URL = 'https://clinicaltrials.gov/api/v2'

# Headers for API requests
HEADERS = {
    'Accept': 'application/json',
    'User-Agent': 'python-requests/2.31.0', # Using requests User-Agent as it works reliably
}

# Connection pooling for better performance
session = requests.Session()
session.headers.update(HEADERS)

PAGE_SIZE_CONFIG = 1000

# Rate limiting: 100 requests per 60 seconds
request_timestamps = deque()

def make_request(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Helper to make synchronous requests to Clinical Trials API.
    Handles rate limiting and consistent headers.
    """
    global request_timestamps
    
    # Prune timestamps older than 60 seconds
    current_time = time.time()
    while request_timestamps and current_time - request_timestamps[0] > 60:
        request_timestamps.popleft()
        
    # Rate limiting: max 100 requests per 60 seconds
    if len(request_timestamps) >= 100:
        # Wait until the oldest request expires
        wait_time = 60 - (current_time - request_timestamps[0])
        if wait_time > 0:
            time.sleep(wait_time)
            # Re-prune after waiting
            current_time = time.time()
            while request_timestamps and current_time - request_timestamps[0] > 60:
                request_timestamps.popleft()
    
    # Add current timestamp
    request_timestamps.append(time.time())

    try:
        # Use session for connection pooling
        response = session.get(
            f"{API_BASE_URL}{endpoint}",
            params=params,
            timeout=30.0
        )
        
        # Handle 404 specifically - return empty result safely
        if response.status_code == 404:
            # Check if we were expecting a list or a single item based on endpoint
            if endpoint.startswith('/studies/'):
                 # Single study endpoint returns 404 if not found
                 return None 
            return {"studies": [], "totalCount": 0}
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 404:
            if endpoint.startswith('/studies/'):
                 return None
            return {"studies": [], "totalCount": 0}
        raise RuntimeError(f"Clinical Trials API error: {str(e)}")

def fetch_studies(endpoint: str, params: Dict[str, Any], limit: int = 10) -> Dict[str, Any]:
    """Fetch studies with pagination until limit is reached or no more results."""
    all_studies = []
    total_count = 0
    next_page_token = None
    
    # Ensure params has format=json
    params['format'] = 'json'

    while len(all_studies) < limit:
        # Calculate max items to fetch in this batch (max 100 per API call)
        remaining = limit - len(all_studies)
        params['pageSize'] = min(remaining, 1000)
        
        if next_page_token:
            params['pageToken'] = next_page_token
            
        data = make_request(endpoint, params)
        studies = data.get("studies", [])
        
        if not studies:
            break
            
        # Check for nextPageToken in the response
        next_page_token = data.get('nextPageToken')
        all_studies.extend(studies)
        total_count += len(studies)

        # Break if there are no more pages
        if not next_page_token:
            break

    return {'studies': all_studies, 'totalCount': total_count}

def format_study_summary(study: Dict[str, Any]) -> Dict[str, Any]:
    """Format study summary from API response"""
    protocol = study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    status = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    sponsor = protocol.get("sponsorCollaboratorsModule", {})
    conditions = protocol.get("conditionsModule", {})
    
    return {
        "nctId": identification.get("nctId"),
        "title": identification.get("briefTitle"),
        "status": status.get("overallStatus"),
        "phase": design.get("phases", ["Not specified"]),
        "studyType": design.get("studyType", "Unknown"),
        "sponsor": sponsor.get("leadSponsor", {}).get("name", "Not specified"),
        "conditions": conditions.get("conditions", [])[:3],
        "startDate": status.get("startDateStruct", {}).get("date", "Not specified")
    }

def format_detailed_study(study: Dict[str, Any]) -> Dict[str, Any]:
    """Format detailed study info from API response"""
    protocol = study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    status_mod = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    sponsor = protocol.get("sponsorCollaboratorsModule", {})
    conditions = protocol.get("conditionsModule", {})
    eligibility = protocol.get("eligibilityModule", {})
    contacts = protocol.get("contactsLocationsModule", {})
    
    return {
        "identification": {
            "nctId": identification.get("nctId"),
            "briefTitle": identification.get("briefTitle"),
            "officialTitle": identification.get("officialTitle")
        },
        "status": {
            "overallStatus": status_mod.get("overallStatus"),
            "startDate": status_mod.get("startDateStruct", {}).get("date"),
            "primaryCompletionDate": status_mod.get("primaryCompletionDateStruct", {}).get("date")
        },
        "design": {
            "studyType": design.get("studyType"),
            "phases": design.get("phases")
        },
        "sponsor": sponsor.get("leadSponsor"),
        "conditions": conditions.get("conditions"),
        "eligibility": eligibility,
        "locations": contacts.get("locations", [])[:10]
    }

@mcp.tool()
def search_studies(
    query: Optional[str] = None,
    condition: Optional[str] = None,
    intervention: Optional[str] = None,
    location: Optional[str] = None,
    phase: Optional[str] = None,
    status: Optional[str] = None,
    sex: Optional[str] = None,
    age: Optional[str] = None,
    pageSize: int = PAGE_SIZE_CONFIG
) -> str:
    """Search for clinical trials with various filters."""
    # Map parameters to API fields
    # query.* fields map to Essie expression syntax searches
    # filter.* fields are used for filtering results
    params = {}
    if query: params['query.term'] = query
    if condition: params['query.cond'] = condition
    if intervention: params['query.intr'] = intervention
    if location: params['query.locn'] = location
    if phase: params['filter.phase'] = phase
    if status: params['filter.overallStatus'] = status
    if sex: params['filter.sex'] = sex
    if age: params['filter.stdAge'] = age
    
    data = fetch_studies('/studies', params, pageSize)
    studies = data.get("studies", [])
    results = [format_study_summary(s) for s in studies]
    
    return json.dumps({
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "studies": results
    }, indent=2)

@mcp.tool()
def get_study_details(nctId: str) -> str:
    """
    Get detailed information about a specific clinical trial.
    
    This tool uses the direct GET /studies/{nctId} endpoint for efficiency.
    """
    # specific endpoint: /studies/{nctId}
    
    if not nctId.startswith('NCT') or not nctId[3:].isdigit():
       return "Error: Valid NCT ID is required (format: NCT########)"

    # Direct endpoint fetch
    # We set fields only if needed, but here we fetch all fields by default (no fields param)
    params = {'format': 'json'}
    data = make_request(f'/studies/{nctId}', params)
    
    if not data:
        return f"No study found with NCT ID: {nctId}"
    
    # The direct endpoint returns the study object directly, unlike /studies which returns {"studies": [...]}
    # The data returned is the study object itself.
    detailed_info = format_detailed_study(data)
    return json.dumps(detailed_info, indent=2)

@mcp.tool()
def search_by_location(
    country: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    facilityName: Optional[str] = None,
    distance: Optional[int] = None,
    pageSize: int = PAGE_SIZE_CONFIG
) -> str:
    """Find clinical trials by geographic location."""
    # Use query.locn for location search which supports various location types
    # filter.distance allows searching within a radius if city/coords are provided
    params = {}
    location_parts = []
    if country: location_parts.append(country)
    if state: location_parts.append(state)
    if city: location_parts.append(city)
    if facilityName: location_parts.append(facilityName)
    
    location_query = ", ".join(location_parts)
    if location_query: params['query.locn'] = location_query
    if distance and city: params['filter.distance'] = distance
        
    data = fetch_studies('/studies', params, pageSize)
    studies = data.get("studies", [])
    
    results = []
    for study in studies:
        summary = format_study_summary(study)
        contacts = study.get("protocolSection", {}).get("contactsLocationsModule", {})
        summary["locations"] = contacts.get("locations", [])[:3]
        results.append(summary)
        
    return json.dumps({
        "searchCriteria": {"locationQuery": location_query, "distance": distance},
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "studies": results
    }, indent=2)

@mcp.tool()
def search_by_condition(
    condition: str,
    phase: Optional[str] = None,
    recruitmentStatus: Optional[str] = None,
    pageSize: int = 100
) -> str:
    """Search for clinical trials focusing on specific medical conditions."""
    # query.cond finds studies matching a condition or disease
    params = {'query.cond': condition}
    if phase: params['filter.phase'] = phase
    if recruitmentStatus: params['filter.overallStatus'] = recruitmentStatus
    
    data = fetch_studies('/studies', params, pageSize)
    studies = data.get("studies", [])
    
    results = []
    for study in studies:
        summary = format_study_summary(study)
        protocol = study.get("protocolSection", {})
        eligibility = protocol.get("eligibilityModule", {})
        summary.update({
            "conditions": protocol.get("conditionsModule", {}).get("conditions", []),
            "eligibility": {
                "sex": eligibility.get("sex", "Unknown"),
                "minimumAge": eligibility.get("minimumAge", "Not specified"),
                "maximumAge": eligibility.get("maximumAge", "Not specified"),
                "healthyVolunteers": eligibility.get("healthyVolunteers", False)
            }
        })
        results.append(summary)
        
    return json.dumps({
        "searchCriteria": {"condition": condition, "phase": phase, "recruitmentStatus": recruitmentStatus},
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "studies": results
    }, indent=2)

@mcp.tool()
def get_trial_statistics(groupBy: Optional[str] = None, filters: Optional[str] = None) -> str:
    """Get aggregate statistics about clinical trials."""
    # Note: We fetch a sample of studies and aggregate locally because the API's 
    # built-in stats endpoints have specific limitations or return different structures.
    # We limit to 1000 studies to prevent timeouts while giving a representative sample.
    params = {}
    limit = PAGE_SIZE_CONFIG
    filter_dict = {}
    if filters:
        try:
            filter_dict = json.loads(filters)
            if filter_dict.get("condition"): params['query.cond'] = filter_dict["condition"]
            if filter_dict.get("phase"): params['filter.phase'] = filter_dict["phase"]
            if filter_dict.get("status"): params['filter.overallStatus'] = filter_dict["status"]
        except json.JSONDecodeError:
            pass

    data = fetch_studies('/studies', params, limit)
    studies = data.get("studies", [])
    
    stats = {}
    if not groupBy:
        stats = {
            "totalStudies": len(studies),
            "byStatus": _group_by_field(studies, "status"),
            "byPhase": _group_by_field(studies, "phase"),
            "byStudyType": _group_by_field(studies, "studyType")
        }
    else:
        stats = _group_by_field(studies, groupBy)
        
    return json.dumps({
        "totalStudies": data.get("totalCount", 0),
        "analyzedStudies": len(studies),
        "groupBy": groupBy or "none",
        "filters": filter_dict,
        "statistics": stats
    }, indent=2)

def _group_by_field(studies: List[Dict], field: str) -> Dict[str, int]:
    groups = {}
    for study in studies:
        protocol = study.get("protocolSection", {})
        value = "Unknown"
        if field == "status":
            value = protocol.get("statusModule", {}).get("overallStatus", "Unknown")
        elif field == "phase":
            phases = protocol.get("designModule", {}).get("phases", [])
            value = phases[0] if phases else "Not specified"
        elif field == "studyType":
            value = protocol.get("designModule", {}).get("studyType", "Unknown")
        elif field == "condition":
            conditions = protocol.get("conditionsModule", {}).get("conditions", [])
            value = conditions[0] if conditions else "Not specified"
        elif field == "sponsor":
            value = protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", "Not specified")
        groups[value] = groups.get(value, 0) + 1
    return groups

@mcp.tool()
def search_by_sponsor(sponsor: str, sponsorType: Optional[str] = None, pageSize: int = 100) -> str:
    """Search clinical trials by sponsor or organization."""
    # query.spons finds studies by sponsor, collaborator, or agency class
    params = {'query.spons': sponsor}
    if sponsorType: params['filter.leadSponsorClass'] = sponsorType
        
    data = fetch_studies('/studies', params, pageSize)
    studies = data.get("studies", [])
    results = []
    for study in studies:
        summary = format_study_summary(study)
        summary["sponsorDetails"] = study.get("protocolSection", {}).get("sponsorCollaboratorsModule", {}).get("leadSponsor")
        results.append(summary)
        
    return json.dumps({
        "searchCriteria": {"sponsor": sponsor, "sponsorType": sponsorType},
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "studies": results
    }, indent=2)

@mcp.tool()
def search_by_intervention(intervention: str, interventionType: Optional[str] = None, phase: Optional[str] = None, pageSize: int = 100) -> str:
    """Search clinical trials by intervention or treatment type."""
    params = {'query.intr': intervention}
    if interventionType: params['filter.interventionType'] = interventionType
    if phase: params['filter.phase'] = phase
    
    data = fetch_studies('/studies', params, pageSize)
    studies = data.get("studies", [])
    results = [format_study_summary(s) for s in studies]
    
    return json.dumps({
        "searchCriteria": {"intervention": intervention, "interventionType": interventionType, "phase": phase},
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "studies": results
    }, indent=2)

@mcp.tool()
def get_recruiting_studies(condition: Optional[str] = None, location: Optional[str] = None, ageGroup: Optional[str] = None, pageSize: int = 100, task_progress: Optional[str] = None) -> str:
    """Get currently recruiting clinical trials with contact information."""
    params = {'filter.overallStatus': 'RECRUITING'}
    if condition: params['query.cond'] = condition
    if location: params['query.locn'] = location
    if ageGroup: params['filter.stdAge'] = ageGroup
    
    data = fetch_studies('/studies', params, pageSize)
    studies = data.get("studies", [])
    results = []
    for study in studies:
        summary = format_study_summary(study)
        protocol = study.get("protocolSection", {})
        eligibility = protocol.get("eligibilityModule", {})
        summary.update({
            "eligibility": {
                "sex": eligibility.get("sex", "Unknown"),
                "minimumAge": eligibility.get("minimumAge", "Not specified"),
                "maximumAge": eligibility.get("maximumAge", "Not specified"),
                "healthyVolunteers": eligibility.get("healthyVolunteers", False)
            },
            "locations": protocol.get("contactsLocationsModule", {}).get("locations", [])[:2]
        })
        results.append(summary)
        
    return json.dumps({
        "searchCriteria": {"recruitmentStatus": "RECRUITING", "condition": condition, "location": location, "ageGroup": ageGroup},
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "studies": results
    }, indent=2)

@mcp.tool()
def search_by_date_range(startDateFrom: Optional[str] = None, startDateTo: Optional[str] = None, completionDateFrom: Optional[str] = None, completionDateTo: Optional[str] = None, condition: Optional[str] = None, pageSize: int = 100) -> str:
    """Search clinical trials by start or completion date range."""
    params = {}
    if startDateFrom: params['filter.studyStartDateFrom'] = startDateFrom
    if startDateTo: params['filter.studyStartDateTo'] = startDateTo
    if completionDateFrom: params['filter.primaryCompletionDateFrom'] = completionDateFrom
    if completionDateTo: params['filter.primaryCompletionDateTo'] = completionDateTo
    if condition: params['query.cond'] = condition
    
    data = fetch_studies('/studies', params, pageSize)
    studies = data.get("studies", [])
    results = []
    for study in studies:
        summary = format_study_summary(study)
        status = study.get("protocolSection", {}).get("statusModule", {})
        summary["dates"] = {
            "startDate": status.get("startDateStruct", {}).get("date"),
            "primaryCompletionDate": status.get("primaryCompletionDateStruct", {}).get("date")
        }
        results.append(summary)
        
    return json.dumps({
        "searchCriteria": {"startDateFrom": startDateFrom, "startDateTo": startDateTo, "completionDateFrom": completionDateFrom, "completionDateTo": completionDateTo, "condition": condition},
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "studies": results
    }, indent=2)

@mcp.tool()
def get_studies_with_results(condition: Optional[str] = None, intervention: Optional[str] = None, completedAfter: Optional[str] = None, pageSize: int = 100) -> str:
    """Find completed clinical trials that have published results."""
    params = {'filter.overallStatus': 'COMPLETED', 'filter.hasResults': True}
    if condition: params['query.cond'] = condition
    if intervention: params['query.intr'] = intervention
    if completedAfter: params['filter.primaryCompletionDateFrom'] = completedAfter
    
    data = fetch_studies('/studies', params, pageSize)
    studies = data.get("studies", [])
    results = []
    for study in studies:
        summary = format_study_summary(study)
        status = study.get("protocolSection", {}).get("statusModule", {})
        summary.update({
            "completionDate": status.get("primaryCompletionDateStruct", {}).get("date"),
            "hasResults": True
        })
        results.append(summary)
        
    return json.dumps({
        "searchCriteria": {"status": "COMPLETED", "hasResults": True, "condition": condition, "intervention": intervention, "completedAfter": completedAfter},
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "studies": results
    }, indent=2)

@mcp.tool()
def search_rare_diseases(rareDisease: str, recruitmentStatus: Optional[str] = None, pageSize: int = 100) -> str:
    """Search clinical trials for rare diseases and orphan conditions."""
    params = {'query.cond': rareDisease, 'query.term': f"{rareDisease} OR orphan OR rare"}
    if recruitmentStatus: params['filter.overallStatus'] = recruitmentStatus
    
    data = fetch_studies('/studies', params, pageSize)
    studies = data.get("studies", [])
    results = []
    for study in studies:
        summary = format_study_summary(study)
        protocol = study.get("protocolSection", {})
        eligibility = protocol.get("eligibilityModule", {})
        summary.update({
            "conditions": protocol.get("conditionsModule", {}).get("conditions", []),
            "eligibility": {
                "sex": eligibility.get("sex", "Unknown"),
                "minimumAge": eligibility.get("minimumAge", "Not specified"),
                "maximumAge": eligibility.get("maximumAge", "Not specified")
            }
        })
        results.append(summary)
        
    return json.dumps({
        "searchCriteria": {"rareDisease": rareDisease, "recruitmentStatus": recruitmentStatus, "searchNote": "Includes orphan and rare disease designations"},
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "studies": results
    }, indent=2)

@mcp.tool()
def get_pediatric_studies(condition: Optional[str] = None, ageRange: Optional[str] = None, recruitmentStatus: Optional[str] = None, pageSize: int = 100) -> str:
    """Find clinical trials specifically designed for children and adolescents."""
    params = {'filter.stdAge': 'CHILD'}
    if condition: params['query.cond'] = condition
    if recruitmentStatus: params['filter.overallStatus'] = recruitmentStatus
    
    if ageRange == 'INFANT':
        params['filter.minimumAge'] = '0 Years'
        params['filter.maximumAge'] = '2 Years'
    elif ageRange == 'CHILD':
        params['filter.minimumAge'] = '2 Years'
        params['filter.maximumAge'] = '12 Years'
    elif ageRange == 'ADOLESCENT':
        params['filter.minimumAge'] = '12 Years'
        params['filter.maximumAge'] = '18 Years'
        
    data = fetch_studies('/studies', params, pageSize)
    studies = data.get("studies", [])
    results = []
    for study in studies:
        summary = format_study_summary(study)
        protocol = study.get("protocolSection", {})
        eligibility = protocol.get("eligibilityModule", {})
        summary.update({
            "conditions": protocol.get("conditionsModule", {}).get("conditions", []),
            "eligibility": {
                "sex": eligibility.get("sex", "Unknown"),
                "minimumAge": eligibility.get("minimumAge", "Not specified"),
                "maximumAge": eligibility.get("maximumAge", "Not specified"),
                "healthyVolunteers": eligibility.get("healthyVolunteers", False)
            },
            "locations": protocol.get("contactsLocationsModule", {}).get("locations", [])[:2]
        })
        results.append(summary)
        
    return json.dumps({
        "searchCriteria": {"targetPopulation": "PEDIATRIC", "condition": condition, "ageRange": ageRange, "recruitmentStatus": recruitmentStatus},
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "studies": results
    }, indent=2)

@mcp.tool()
def get_similar_studies(nctId: str, similarityType: str = 'CONDITION', pageSize: int = 100) -> str:
    """Find clinical trials similar to a specific study by NCT ID."""
    if not nctId.startswith('NCT'): return "Error: Valid NCT ID is required"
    
    ref_params = {'format': 'json', 'query.term': nctId, 'pageSize': 1}
    ref_data = make_request('/studies', ref_params)
    ref_studies = ref_data.get("studies", [])
    if not ref_studies: return f"Reference study not found: {nctId}"
    
    
    ref_study = ref_studies[0]
    protocol = ref_study.get("protocolSection", {})
    search_params = {}
    
    if similarityType == 'CONDITION':
        conditions = protocol.get("conditionsModule", {}).get("conditions", [])
        if conditions: search_params['query.cond'] = conditions[0]
    elif similarityType == 'SPONSOR':
        sponsor = protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name")
        if sponsor: search_params['query.spons'] = sponsor
    elif similarityType == 'PHASE':
        phases = protocol.get("designModule", {}).get("phases", [])
        if phases: search_params['filter.phase'] = phases[0]
        
    data = fetch_studies('/studies', search_params, pageSize)
    studies = data.get("studies", [])
    results = [format_study_summary(s) for s in studies if s.get("protocolSection", {}).get("identificationModule", {}).get("nctId") != nctId]
    
    return json.dumps({
        "referenceStudy": {"nctId": nctId, "title": protocol.get("identificationModule", {}).get("briefTitle")},
        "similarityType": similarityType,
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "similarStudies": results
    }, indent=2)

@mcp.tool()
def search_by_primary_outcome(outcome: str, condition: Optional[str] = None, phase: Optional[str] = None, pageSize: int = 100) -> str:
    """Search clinical trials by primary outcome measures or endpoints."""
    params = {'query.outc': outcome}
    if condition: params['query.cond'] = condition
    if phase: params['filter.phase'] = phase
    
    data = fetch_studies('/studies', params, pageSize)
    studies = data.get("studies", [])
    results = [format_study_summary(s) for s in studies]
    
    return json.dumps({
        "searchCriteria": {"primaryOutcome": outcome, "condition": condition, "phase": phase},
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "studies": results
    }, indent=2)

@mcp.tool()
def search_by_eligibility_criteria(
    minAge: Optional[str] = None,
    maxAge: Optional[str] = None,
    sex: Optional[str] = None,
    healthyVolunteers: Optional[bool] = None,
    condition: Optional[str] = None,
    inclusionKeywords: Optional[str] = None,
    exclusionKeywords: Optional[str] = None,
    pageSize: int = PAGE_SIZE_CONFIG
) -> str:
    """Advanced search based on detailed eligibility criteria."""
    params = {}
    if minAge: params['filter.minimumAge'] = minAge
    if maxAge: params['filter.maximumAge'] = maxAge
    if sex: params['filter.sex'] = sex
    if healthyVolunteers is not None: params['filter.healthyVolunteers'] = healthyVolunteers
    if condition: params['query.cond'] = condition
    if inclusionKeywords: params['query.eligibility'] = inclusionKeywords
    
    data = fetch_studies('/studies', params, pageSize)
    studies = data.get("studies", [])
    exclusion_words = exclusionKeywords.lower().split() if exclusionKeywords else []
    results = []
    
    for study in studies:
        protocol = study.get("protocolSection", {})
        eligibility = protocol.get("eligibilityModule", {})
        criteria = eligibility.get("eligibilityCriteria", "")
        if exclusion_words and any(word in criteria.lower() for word in exclusion_words):
            continue
        summary = format_study_summary(study)
        summary["eligibility"] = {
            "sex": eligibility.get("sex", "Unknown"),
            "minimumAge": eligibility.get("minimumAge", "Not specified"),
            "maximumAge": eligibility.get("maximumAge", "Not specified"),
            "healthyVolunteers": eligibility.get("healthyVolunteers", False),
            "criteriaPreview": criteria[:200] + "..." if criteria else "Not available"
        }
        results.append(summary)
        
    return json.dumps({
        "searchCriteria": {"minAge": minAge, "maxAge": maxAge, "sex": sex, "healthyVolunteers": healthyVolunteers, "condition": condition, "inclusionKeywords": inclusionKeywords, "exclusionKeywords": exclusionKeywords},
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "studies": results
    }, indent=2)

@mcp.tool()
def get_study_timeline(condition: Optional[str] = None, sponsor: Optional[str] = None, phase: Optional[str] = None, timelineType: str = 'CURRENT', pageSize: int = 100) -> str:
    """Get detailed timeline and milestone information for studies."""
    params = {}
    if condition: params['query.cond'] = condition
    if sponsor: params['query.spons'] = sponsor
    if phase: params['filter.phase'] = phase
    
    if timelineType == 'CURRENT':
        params['filter.overallStatus'] = 'RECRUITING,NOT_YET_RECRUITING,ACTIVE_NOT_RECRUITING'
    elif timelineType == 'COMPLETED':
        params['filter.overallStatus'] = 'COMPLETED'
    elif timelineType == 'UPCOMING':
        params['filter.overallStatus'] = 'NOT_YET_RECRUITING'
    
    data = fetch_studies('/studies', params, pageSize)
    studies = data.get("studies", [])
    results = []
    for study in studies:
        summary = format_study_summary(study)
        status = study.get("protocolSection", {}).get("statusModule", {})
        summary["timeline"] = {
            "startDate": status.get("startDateStruct", {}).get("date"),
            "primaryCompletionDate": status.get("primaryCompletionDateStruct", {}).get("date"),
            "status": status.get("overallStatus"),
            "daysFromStart": None
        }
        results.append(summary)
        
    return json.dumps({
        "searchCriteria": {"condition": condition, "sponsor": sponsor, "phase": phase, "timelineType": timelineType},
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "studies": results
    }, indent=2)

@mcp.tool()
def search_international_studies(condition: Optional[str] = None, excludeCountry: Optional[str] = None, includeCountry: Optional[str] = None, minCountries: int = 2, phase: Optional[str] = None, pageSize: int = 100) -> str:
    """Find multi-country international clinical trials."""
    params = {}
    if condition: params['query.cond'] = condition
    if phase: params['filter.phase'] = phase
    if includeCountry: params['query.locn'] = includeCountry
    
    data = fetch_studies('/studies', params, pageSize)
    studies = data.get("studies", [])
    results = []
    
    for study in studies:
        contacts = study.get("protocolSection", {}).get("contactsLocationsModule", {})
        locations = contacts.get("locations", [])
        countries = list(set(loc.get("country") for loc in locations if loc.get("country")))
        if len(countries) < minCountries: continue
        if excludeCountry and excludeCountry in countries: continue
        
        summary = format_study_summary(study)
        summary["internationalDetails"] = {
            "totalCountries": len(countries),
            "countries": countries,
            "totalLocations": len(locations),
            "sampleLocations": locations[:3]
        }
        results.append(summary)
        
    return json.dumps({
        "searchCriteria": {"condition": condition, "excludeCountry": excludeCountry, "includeCountry": includeCountry, "minCountries": minCountries, "phase": phase},
        "totalCount": data.get("totalCount", 0),
        "resultsShown": len(results),
        "internationalStudies": results
    }, indent=2)

if __name__ == "__main__":
    mcp.run()
