import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain.tools import tool
import duckdb
from dotenv import load_dotenv
import os

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
dp = Dispatcher()
checkpointer = MemorySaver()
agent = None


@tool
def get_skills_by_employer() -> str:
    """Fetches the list of skills by employer from the DuckDB database."""
    conn = duckdb.connect(database=os.getenv("DUCKDB_PATH"), read_only=True)
    result = conn.execute("select * from main.skill_by_employeer").fetchdf()
    conn.close()
    return result.to_string()


@tool
def get_skill_combinations() -> str:
    """Fetches the list of skill combinations from the DuckDB database."""
    conn = duckdb.connect(database=os.getenv("DUCKDB_PATH"), read_only=True)
    result = conn.execute("select * from main.skill_combinations").fetchdf()
    conn.close()
    return result.to_string()


@tool
def get_skill_by_experience() -> str:
    """Fetches the list of skills by experience level from the DuckDB database."""
    conn = duckdb.connect(database=os.getenv("DUCKDB_PATH"), read_only=True)
    result = conn.execute("select * from main.skill_by_experience").fetchdf()
    conn.close()
    return result.to_string()


@tool
def get_skill_frequency() -> str:
    """Fetches the frequency of skills from the DuckDB database."""
    conn = duckdb.connect(database=os.getenv("DUCKDB_PATH"), read_only=True)
    result = conn.execute("select * from main.skill_frequency").fetchdf()
    conn.close()
    return result.to_string()


custom_tools = [
    get_skills_by_employer,
    get_skill_combinations,
    get_skill_by_experience,
    get_skill_frequency,
]

agent_prompt = """
    You are a data engineering skill advisor for the Kazakhstan job market.
    Your goal is to help users understand skill demand, identify their gaps, and get actionable learning recommendations based on real vacancy data from hh.ru.

    ## Data Available
    You have access to the following tables in DuckDB:

    **Aggregated tables (use custom tools — fast and optimized):**
    - `skill_frequency` — overall skill demand: skill name, vacancy count, % of vacancies
    - `skill_by_experience` — skill demand broken down by experience level (No experience, 1-3 years, 3-6 years, 6+ years)
    - `skill_combinations` — skills that co-occur most often in the same vacancy
    - `skill_by_employeer` — skills demanded by specific employers

    **Raw tables (use DuckDB SQL tool — for complex or custom queries only):**
    - `hh_vacancies` — all vacancy data with columns:
    vacancy_id, title, employer_name, employer_url,
    salary_from, salary_to, currency, salary_is_gross,
    experience_id, experience_name, employment_id, employment_name,
    area_name, area_id, key_skills, description,
    published_at, fetched_at, _query, vacancy_url, archived

    - `hh_skills` — all skills extracted from vacancies with columns, join with `hh_vacancies` on `vacancy_id` for detailed analysis:
    vacancy_id, skill_name

    ## Tool Usage Rules
    1. Always try custom tools first — they are faster and pre-optimized
    2. Use the DuckDB SQL tool only when custom tools cannot answer the question
    3. When writing SQL, always add LIMIT to avoid large results
    4. Never modify data — read only

    ## How to Help Users
    - Ask for the user's current skills if not provided
    - Compare their skills against `skill_frequency` to identify gaps
    - Use `skill_by_experience` to tailor advice to their target level
    - Use `skill_combinations` to suggest what to learn next based on what they already know
    - Be specific and actionable — rank recommendations by market demand
"""


async def get_agent():
    client = MultiServerMCPClient({
        "duckdb": {
            "command": "uvx",
            "args": ["mcp-server-duckdb", "--db-path", os.getenv("DUCKDB_PATH"), "--readonly"],
            "transport": "stdio",
        }
    })
    mcp_tools = await client.get_tools()
    llm = ChatOpenAI(model="gpt-4.1-nano", temperature=0)
    return create_agent(
        llm,
        custom_tools + mcp_tools,
        checkpointer=checkpointer,
        system_prompt=agent_prompt
    )


@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Hi! I'm your DATA Skill advisor.\n\n"
        "Tell me your current skills and I'll show you what the market demands."
    )


@dp.message()
async def handle_message(message: types.Message):
    await message.answer("Thinking...")
    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": message.text}]},
        config={"configurable": {"thread_id": str(message.from_user.id)}}
    )
    await message.answer(response["messages"][-1].content)


async def main():
    global agent
    agent = await get_agent()
    await dp.start_polling(bot)


asyncio.run(main())
