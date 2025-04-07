# intent_service.py

def match_any(keywords, query_lower):
    return any(kw in query_lower.lower() for kw in keywords)

def detect_user_intents(query_lower):
    """
    Detects all high-level intents based on keywords in the user query.
    Returns a dictionary of boolean flags.
    """
    return {
        "wants_rejection_data": match_any([
            "rejection data", "rejection table", "show rejection table", "show rejection data"
        ], query_lower),

        "wants_rejection_chart": match_any([
            "rejection chart", "rejection trend", "trend", "bar graph",
            "rejection bar chart", "trend chart", "rejection rate chart", "rejection data and chart","rejecti"
            "on detail","rejection details"
        ], query_lower),

        "wants_fishbone": match_any([
            "fishbone diagram", "cause and effect", "cause-effect",
            "fba", "diagram", "root cause", "defect analysis diagram"
        ], query_lower),

        "wants_summary": match_any([
            "summary", "summarize", "summary data", "summary table", "top parameters", "top parameter",
            "change summary", "absolute change"
        ], query_lower),

        "wants_all_charts": match_any([
            "all charts", "three charts", "show all charts",
            "analysis plots", "all plots", "3 plots", "all comparison charts"
        ], query_lower),

        "wants_analysis": match_any([
            "fishbone analysis", "rejection rate analysis",
            "compare on", "comparison on", "rejection on the months",
            "compare with", "do analysis", "compare analyze", "compare data"
        ], query_lower),

        "wants_companalysis": match_any([
            "fishbone comparison", "comparison and analysis between",
            "compare on the periods", "rejection rate analysis on the months",
            "compare and analyze between", "compare between", "comparison between",
            "compare and analyse", "comparing", "comparison", "relative difference", "compare and analyze"
        ], query_lower),

        "sql_query": match_any([
            "rejection rate", "rejection percentage", "total rejection", "how many defects",
            "average rejection", "show me", "fetch", "what is the rejection", "in the month",
            "defect rate", "defect percentage", "monthly rejection", "production",
            "defect count", "defect_type", "date", "shift", "group name",
            "component id", "total production", "total rejection",
            "daily", "defects", "give sql", "ask_sql", "query database"
        ], query_lower),

        "wants_distribution": "distribution" in query_lower,
        "wants_box": "box" in query_lower,
        "wants_correlation": "correlation" in query_lower
    }
