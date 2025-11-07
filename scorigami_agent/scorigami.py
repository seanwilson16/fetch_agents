from uagents import Model, Field
import logging
import pandas as pd

df = pd.read_csv("score_history.csv")

class scorigamiRequest(Model):
    team1_score: int
    team2_score: int

class scorigamiResponse(Model):
    score: str
    possible: bool
    occurred: bool
    count: int | None
    latest: str | None

async def get_scorigami_from_score(team1_score: int, team2_score: int) -> scorigamiResponse:
    """
    From any positive integer final score, will return whether that score
    is possible, whether that score has occurred, how many times, and what
    the latest game with that score was.

    Args:
        team1_score: int representing the score of the first team
        team2_score: int representing the score of the second team

    Returns:
        scorigamiResponse object containing raw results
    """
    IMPOSSIBLE_SCORES = {
    "1-0", "1-1", "2-1", "3-1", "4-1", "5-1", "7-1"
    }

    try:
        score1, score2 = sorted([team1_score, team2_score], reverse=True)
        score_str = f"{score1}-{score2}"

        if score_str in IMPOSSIBLE_SCORES:
            return scorigamiResponse(
                score=score_str,
                possible=False,
                occurred=False,
                count=None,
                latest=None
            )

        row = df[df["Score"] == score_str]

        if row.empty:
            return scorigamiResponse(
                score=score_str,
                possible=True,
                occurred=False,
                count=None,
                latest=None
            )
        else:
            count = int(row["Count"].values[0])
            last_game = row["Last Game"].values[0]
            return scorigamiResponse(
                score=score_str,
                possible=True,
                occurred=True,
                count=count,
                latest=last_game
            )

    except Exception as e:
        return scorigamiResponse(
            score=score_str,
            possible=False,
            occurred=False,
            count=None,
            latest=None,
        )
