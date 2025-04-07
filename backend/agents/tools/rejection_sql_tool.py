# agents/tools/rejection_sql_tool.py

from langchain.tools import tool
from sqlalchemy import create_engine, text
import os

@tool
def query_rejection_rate(defect: str, month: str, foundry: str) -> str:
    """Query average rejection rate from the SQL database."""
    try:
        db_user = os.getenv("DB_USER")
        db_pass = os.getenv("DB_PASS")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT")
        db_name = os.getenv("DB_NAME")
        mysql_url = f"mysql+mysqlconnector://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        engine = create_engine(mysql_url)

        with engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT AVG(`{defect}_%`) as avg_rejection
                FROM rejection_{foundry.lower()}
                WHERE `Production Date` LIKE :month
            """), {"month": f"{month}%"})
            avg = result.scalar()
            return f"Average rejection rate for {defect} in {month} is {avg:.2f}%"
    except Exception as e:
        return f"SQL Query Failed: {e}"
