from uagents import Model, Field
import logging
from election_data import data
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResultsRequest(Model):
    state: str
    year: int

class CandidateResult(Model):
    candidate: str
    party_detailed: str
    candidatevotes: int
    totalvotes: int

class ResultsResponse(Model):
    state: str
    year: int
    results: list[CandidateResult]

def reformat_name(name: str) -> str:
    if "," in name:
        last, first = name.split(",", 1)
        return first.strip() + " " + last.strip()
    return name.strip()

async def get_results_from_state_yr(state: str, year: int) -> ResultsResponse:
    """
    Get election results for each candidate who received
    votes in the given state and election year

    Args:
        state: state name in string format
        year: election year in int format

    Returns:
        ResultsResponse object containing raw results
    """
    try:
        logger.info(f"Looking up results for {state}, {year}")
        norm_state = state.strip().upper()

        filtered = [
            row for row in data
            if row["year"] == year and
               row["state"].strip().upper() == norm_state and
               row.get("candidatevotes") is not None and
               not (isinstance(row["candidatevotes"], float) and math.isnan(row["candidatevotes"]))
        ]

        if not filtered:
            logger.warning(f"No results found for {state.title()} in {year}.")
            return ResultsResponse(state=state, year=year, results=[])

        # Sort by votes descending
        filtered.sort(key=lambda x: x["candidatevotes"], reverse=True)

        results = []
        for row in filtered:
            candidate = reformat_name(row["candidate"].title())
            party = row["party_detailed"].title()


            candidatevotes = int(row["candidatevotes"])
            totalvotes = int(row["totalvotes"]) if row.get("totalvotes") else 0

            results.append(CandidateResult(
                candidate=candidate,
                party_detailed=party,
                candidatevotes=candidatevotes,
                totalvotes=totalvotes,
            ))

        logger.info(f"Parsed {len(results)} results for {state.title()} in {year}")
        return ResultsResponse(state=state, year=year, results=results)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return ResultsResponse(state=state, year=year, results=[])
