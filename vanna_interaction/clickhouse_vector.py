import json
from typing import List
import clickhouse_connect
import pandas as pd
from vanna.base import VannaBase
from vanna.utils import deterministic_uuid
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from vanna.ollama import Ollama
from vanna.vllm import Vllm
import ollama

default_ef = embedding_functions.DefaultEmbeddingFunction()


class ClickHouse_VectorStore(VannaBase):
    def __init__(self, config=None):
        # VannaBase.__init__(self, config=config)
        self.config = config or {}
        self.embedding_function = config.get("embedding_function", default_ef)
        collection_metadata = config.get("collection_metadata", None)
        # Initialize ClickHouse client
        self.client = clickhouse_connect.get_client(
            host=self.config.get("host", ""),
            port=self.config.get("port", 8443),
            username=self.config.get("username", "default"),
            password=self.config.get("password", ""),
            database=self.config.get("database", "default")
        )

        # Create required tables if they don't exist
        self._create_tables()



    def _create_tables(self):
        self.client.command("""
        CREATE TABLE IF NOT EXISTS vector_data (
            id String,
            embedding Array(Float64),
            text String,
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY id;
        """)

        self.client.command("""
        CREATE TABLE IF NOT EXISTS question_sql (
            id String,
            question String,
            sql_query String,
            embedding Array(Float64),
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY id;
        """)

        self.client.command("""
        CREATE TABLE IF NOT EXISTS ddl_statements (
            id String,
            ddl String,
            embedding Array(Float64),
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY id;
        """)

    # def generate_embedding(self, data: str, **kwargs) -> List[float]:
    #         embedding = self.embedding_function(data)
    #         return embedding

    def generate_embedding(self, data: str, **kwargs) -> List[float]:
        embedding = ollama.embeddings(model="llama3.2", prompt=data)
        return embedding['embedding']

    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        id = deterministic_uuid(question) + "-sql"
        embedding = self.generate_embedding(question)
        self.client.insert(
            "question_sql",
            [[id, question, sql, embedding]],
            column_names=["id", "question", "sql_query", "embedding"]
        )
        return id

    def add_ddl(self, ddl: str, **kwargs) -> str:
        id = deterministic_uuid(ddl) + "-ddl"
        embedding = self.generate_embedding(ddl)
        self.client.insert(
            "ddl_statements",
            [[id, ddl, embedding]],
            column_names=["id", "ddl", "embedding"]
        )
        return id

    def add_documentation(self, documentation: str, **kwargs) -> str:
        id = deterministic_uuid(documentation) + "-doc"
        embedding = self.generate_embedding(documentation)
        #print(embedding)
        self.client.insert(
            "vector_data",
            [[id, embedding, documentation]],
            column_names=["id", "embedding", "text"]
        )
        return id

    def get_training_data(self, **kwargs) -> pd.DataFrame:
        result = self.client.query("SELECT id, question, sql_query FROM question_sql")
        return pd.DataFrame(result.result_rows, columns=["id", "question", "sql_query"])

    def remove_training_data(self, id: str, **kwargs) -> bool:
        table = "question_sql" if "-sql" in id else "ddl_statements" if "-ddl" in id else "vector_data"
        self.client.command(f"ALTER TABLE {table} DELETE WHERE id = %(id)s", {"id": id})
        return True

    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        embedding = self.generate_embedding(question)
        query = """
        SELECT question, sql_query, cosineDistance(embedding, %(embedding)s) AS similarity
        FROM question_sql
        ORDER BY similarity ASC
        LIMIT 5
        """
        result = self.client.query(query, {"embedding": embedding})
        return [{"question": row[0], "sql": row[1], "similarity": row[2]} for row in result.result_rows]

    def get_related_ddl(self, question: str, **kwargs) -> list:
        embedding = self.generate_embedding(question)
        query = """
        SELECT ddl, cosineDistance(embedding, %(embedding)s) AS similarity
        FROM ddl_statements
        ORDER BY similarity ASC
        LIMIT 5
        """
        result = self.client.query(query, {"embedding": embedding})
        return [row[0] for row in result.result_rows]

    def get_related_documentation(self, question: str, **kwargs) -> list:
        embedding = self.generate_embedding(question)
        query = """
        SELECT text, cosineDistance(embedding, %(embedding)s) AS similarity
        FROM vector_data
        ORDER BY similarity ASC
        LIMIT 5
        """
        result = self.client.query(query, {"embedding": embedding})
        return [row[0] for row in result.result_rows]


class MyVanna(ClickHouse_VectorStore, Ollama):
    def __init__(self, config=None):
      # ChromaDB_VectorStore.__init__(self, config=config)
      ClickHouse_VectorStore.__init__(self, config=config)
      # Vllm.__init__(self, config=config)
      Ollama.__init__(self, config=config)
      self.run_sql_is_set = False
      self.static_documentation = ""
      self.dialect = self.config.get("dialect", "SQL")
      self.language = self.config.get("language", None)
      self.max_tokens = self.config.get("max_tokens", 14000)

vn = MyVanna(config={'model': 'llama3.2'})

############ Tests ###########

vn.connect_to_clickhouse(host='',
                            dbname='default',
                            user='default',
                            password='',
                            port=8443)

# df_ddl = vn.run_sql('SELECT * FROM vmCloud_data')
# # print(df_ddl)

# ddl_input = "CREATE TABLE vmCloud_data (vm_id String, timestamp DateTime, cpu_usage Float64, memory_usage Float64, network_traffic Float64, power_consumption Float64, num_executed_instructions Float64, execution_time Float64, energy_efficiency Float64, task_type String, task_priority String)"
# vn.train(ddl=ddl_input)

# vn.train(documentation='Our data defines vm cloud server data that includes cpu usage, memory usage, network traffic, power consumption, instructions executed, execution time, energy efficiency, task type, task priority, and task status.')

# vn.train(sql="SELECT * FROM vmCloud_data")

# vn.train(question="What is the server data from january 25th, 2023?",
#          sql="SELECT * FROM vmCloud_data WHERE timestamp>='2023-01-25 00:00:00' AND timestamp<'2023-01-26 00:00:00';")

# vn.train(question="How much cpu and memory was used on june 15th, 2023?",
#          sql="SELECT cpu_usage, memory_usage, timestamp FROM vmCloud_data WHERE timestamp>='2023-06-15 00:00:00' AND timestamp<'2023-06-16 00:00:00';")

# vn.train(question="How much cpu and memory was used on july 19th, 2023?",
#          sql="SELECT cpu_usage, memory_usage, timestamp FROM vmCloud_data WHERE timestamp>='2023-07-19 00:00:00' AND timestamp<'2023-07-20 00:00:00';")

# vn.train(question=)

training_data = vn.get_training_data()
print(training_data)

result = vn.ask(question="What was the server data from january 25th 2023? Include timestamps with the data.")
