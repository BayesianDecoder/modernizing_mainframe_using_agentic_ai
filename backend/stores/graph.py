"""Neo4j knowledge graph — load from parsed COBOL/JCL, query via Cypher."""
import os
from neo4j import GraphDatabase

_driver = None

def driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USERNAME", "neo4j"),
                  os.getenv("NEO4J_PASSWORD", "password")),
        )
    return _driver

def run(cypher: str, **params) -> list[dict]:
    with driver().session() as s:
        return [dict(r) for r in s.run(cypher, **params)]

def create_schema():
    with driver().session() as s:
        s.run("CREATE CONSTRAINT program_name IF NOT EXISTS FOR (p:Program) REQUIRE p.name IS UNIQUE")
        s.run("CREATE CONSTRAINT job_name     IF NOT EXISTS FOR (j:Job)     REQUIRE j.name IS UNIQUE")
        s.run("CREATE CONSTRAINT dataset_name IF NOT EXISTS FOR (d:Dataset) REQUIRE d.name IS UNIQUE")
        s.run("CREATE CONSTRAINT lpar_name    IF NOT EXISTS FOR (l:LPAR)    REQUIRE l.name IS UNIQUE")

def clear():
    with driver().session() as s:
        s.run("MATCH (n) DETACH DELETE n")

def load_programs(programs: list[dict]):
    with driver().session() as s:
        for p in programs:
            s.run("""
                MERGE (x:Program {name:$name})
                SET x.complexity=$complexity, x.lines=$lines,
                    x.description=$description, x.author=$author
            """, name=p["name"], complexity=p.get("complexity_score",0),
                 lines=p.get("lines",0),
                 description=(p.get("description") or "")[:120],
                 author=p.get("author",""))

def load_jobs(jobs: list[dict]):
    with driver().session() as s:
        for j in jobs:
            s.run("""
                MERGE (x:Job {name:$name})
                SET x.schedule=$schedule, x.sla=$sla,
                    x.lpar=$lpar, x.owner=$owner
            """, name=j["name"], schedule=j.get("schedule",""),
                 sla=j.get("sla",""), lpar=j.get("lpar",""),
                 owner=j.get("owner",""))

def load_relationships(programs: list[dict], jobs: list[dict]):
    known_programs = {p["name"] for p in programs}
    with driver().session() as s:
        # Program CALLS Program
        for p in programs:
            for called in p.get("calls", []):
                s.run("""
                    MERGE (a:Program {name:$a})
                    MERGE (b:Program {name:$b})
                    MERGE (a)-[:CALLS]->(b)
                """, a=p["name"], b=called)

        # Job EXECUTES Program — skip JCL steps that run IBM utilities
        # (e.g. IEFBR14, a no-op used for dataset allocation checks) rather
        # than one of our actually-parsed COBOL programs.
        for j in jobs:
            for pgm in j.get("programs", []):
                if pgm not in known_programs:
                    continue
                s.run("""
                    MERGE (job:Job {name:$j})
                    MERGE (pgm:Program {name:$p})
                    MERGE (job)-[:EXECUTES]->(pgm)
                """, j=j["name"], p=pgm)

            # Job TRIGGERS Job
            for trig in j.get("triggers", []):
                s.run("""
                    MERGE (a:Job {name:$a})
                    MERGE (b:Job {name:$b})
                    MERGE (a)-[:TRIGGERS]->(b)
                """, a=j["name"], b=trig)

            # Job RUNS_ON LPAR
            if j.get("lpar"):
                s.run("""
                    MERGE (job:Job {name:$j})
                    MERGE (lpar:LPAR {name:$l})
                    MERGE (job)-[:RUNS_ON]->(lpar)
                """, j=j["name"], l=j["lpar"])

        # Program READS / WRITES Dataset
        for p in programs:
            for dsn in p.get("reads", []):
                s.run("""
                    MERGE (prog:Program {name:$p})
                    MERGE (ds:Dataset {name:$d})
                    MERGE (prog)-[:READS]->(ds)
                """, p=p["name"], d=dsn)

def stats() -> dict:
    with driver().session() as s:
        r = s.run("""
            MATCH (p:Program) WITH count(p) AS prg
            MATCH (j:Job)     WITH prg, count(j) AS jobs
            MATCH (d:Dataset) WITH prg, jobs, count(d) AS ds
            RETURN prg, jobs, ds
        """).single()
    return dict(r) if r else {}
