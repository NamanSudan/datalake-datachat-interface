import clickhouse_connect
import clickhouse_driver
from clickhouse_driver import Client
#from clickhouse_connect.driver.httpclient import HttpClient
import pandas as pd
import vanna
from typing import List
import ollama

from vanna.base import VannaBase
from vanna.ollama import Ollama
from vanna.chromadb import ChromaDB_VectorStore


class MyCustomVectorDB(VannaBase):
  def __init__(self, config=None):
      self.config = config or {}
   #   self.client = Client(
   #      host=self.config.get("host", "by8y1h0mfc.us-west-2.aws.clickhouse.cloud"),
   #      port=self.config.get("port", 8443),
   #      user=self.config.get("user", "default"),
   #      password=self.config.get("password", "u.XyyiQGvIUB2"),
   #      database=self.config.get("database", "default"),
   #      secure=True
   #   )
      # self.client = clickhouse_connect.get_client(host="by8y1h0mfc.us-west-2.aws.clickhouse.cloud", username="default", password="u.XyyiQGvIUB2", port=8443)
      self.client = clickhouse_connect.get_client(
            host="by8y1h0mfc.us-west-2.aws.clickhouse.cloud",
            username="default",
            password="u.XyyiQGvIUB2",
            port=8443
        )

  def add_ddl(self, ddl: str, **kwargs) -> str:
     try:
        self.client.command(ddl)
        return "DDL added successfully"
     except Exception as e:
        return f"Error adding DDL: {str(e)}"

  def add_documentation(self, doc: str, **kwargs) -> str:
      try:
         embedding = self.generate_embedding(doc)
         # print(embedding, doc)
         data = [[embedding, doc]]
         self.client.insert("vector_data", data, column_names=["embedding", "text"])
         return "Documentation added successfully."
      except Exception as e:
         raise RuntimeError(f"Error adding documentation: {e}")

  def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
      try:
         data = [[question, sql]]
         self.client.insert("question_sql", data, column_names=["question", "sql_query"])
         return "Question-SQL pair added successfully."
      except Exception as e:
         raise RuntimeError(f"Error adding Question-SQL pair: {e}")

  def get_related_ddl(self, question: str, **kwargs) -> list:
      try:
         result = self.client.query("SELECT ddl FROM ddl_table WHERE ddl LIKE %(query)s", {"query": f"%{question}%"})
         return [row["ddl"] for row in result]
      except Exception as e:
         raise RuntimeError(f"Error retrieving related DDL: {e}")

  def get_related_documentation(self, question: str, **kwargs) -> list:
      try:
         result = self.client.query("SELECT text FROM vector_data WHERE text LIKE %(query)s", {"query": f"%{question}%"})
         return [row["text"] for row in result]
      except Exception as e:
         raise RuntimeError(f"Error retrieving related documentation: {e}")

  def get_similar_question_sql(self, question: str, **kwargs) -> list:
      query_embedding = self.generate_embedding(question)
      try:
         result = self.client.query(
               """
               SELECT question, sql
               FROM question_sql
               ORDER BY cosineDistance(vector_embedding, %(query_embedding)s) ASC
               LIMIT 5
               """,
               {"query_embedding": query_embedding}
         )
         return [{"question": row["question"], "sql": row["sql"]} for row in result]
      except Exception as e:
         raise RuntimeError(f"Error retrieving similar question-SQL pairs: {e}")


  def get_training_data(self, **kwargs) -> pd.DataFrame:
      try:
         result = self.client.query("SELECT question, sql FROM question_sql")
         return pd.DataFrame(result, columns=["question", "sql"])
      except Exception as e:
         raise RuntimeError(f"Error retrieving training data: {e}")

  def remove_training_data(self, id: str, **kwargs) -> bool:
      try:
         self.client.command("ALTER TABLE question_sql DELETE WHERE id = %(id)s", {"id": id})
         return True
      except Exception as e:
         raise RuntimeError(f"Error removing training data: {e}")
  
  def generate_embedding(self, data: str, **kwargs) -> List[float]:
      try:
         embedding = ollama.embeddings(model="llama3.2", prompt=data)
         return embedding['embedding']
      except Exception as e:
         raise RuntimeError(f"Error generating embedding: {e}")
  
class MyVanna(MyCustomVectorDB, Ollama):
    def __init__(self, config=None):
      #ChromaDB_VectorStore.__init__(self, config=config)
      MyCustomVectorDB.__init__(self, config=config)
      Ollama.__init__(self, config=config)
      self.run_sql_is_set = False
      self.static_documentation = ""
      self.dialect = self.config.get("dialect", "SQL")
      self.language = self.config.get("language", None)
      self.max_tokens = self.config.get("max_tokens", 14000)

vn = MyVanna(config={'model': 'llama3.2'})

vn.connect_to_clickhouse(host='by8y1h0mfc.us-west-2.aws.clickhouse.cloud',
                            dbname='default',
                            user='default',
                            password='u.XyyiQGvIUB2',
                            port=8443)

############
# ddl_input = "CREATE TABLE IF NOT EXISTS vmCloud_data (vm_id String, timestamp DateTime, cpu_usage Float64, memory_usage Float64, network_traffic Float64, power_consumption Float64, num_executed_instructions Float64, execution_time Float64, energy_efficiency Float64, task_type String, task_priority String)"

# df_information_schema = vn.run_sql("SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'vmCloud_data'")
# # print(df_information_schema)

# plan = vn.get_training_plan_generic(df_information_schema)

# print(plan)

# vn.train(plan=plan)

# vn.train(ddl=ddl_input)

# vn.train(documentation="Our data defines vm cloud server data that includes cpu usage, memory usage, network traffic, power consumption, instructions executed, execution time, energy efficiency, task type, task priority, and task status.")

# vn.train(question="What is the server data from january 25th, 2023?",
#          sql="SELECT * FROM vmCloud_data WHERE timestamp>='2023-01-25 00:00:00' AND timestamp<'2023-01-26 00:00:00';")

# vn.train(question="How much cpu and memory was used on june 15th, 2023?",
#          sql="SELECT cpu_usage, memory_usage, timestamp FROM vmCloud_data WHERE timestamp>='2023-06-15 00:00:00' AND timestamp<'2023-06-16 00:00:00';")

# vn.train(question="How much cpu and memory was used on july 19th, 2023?",
#          sql="SELECT cpu_usage, memory_usage, timestamp FROM vmCloud_data WHERE timestamp>='2023-07-19 00:00:00' AND timestamp<'2023-07-20 00:00:00';")

vn.ask("What is the server data from january 25th, 2023?")

############

# df_ddl = vn.run_sql('SELECT * FROM vmCloud_data')
# # print(df_ddl)

# ddl_input = "CREATE TABLE vmCloud_data (vm_id String, timestamp DateTime, cpu_usage Float64, memory_usage Float64, network_traffic Float64, power_consumption Float64, num_executed_instructions Float64, execution_time Float64, energy_efficiency Float64, task_type String, task_priority String)"
# #vn.train(ddl=ddl_input)

# vn.train(documentation='Our data defines vm cloud server data that includes cpu usage, memory usage, network traffic, power consumption, instructions executed, execution time, energy efficiency, task type, task priority, and task status.')

# vn.train(sql="SELECT * FROM vmCloud_data")

# vn.train(question="What is the server data from january 25th, 2023?",
#          sql="SELECT * FROM vmCloud_data WHERE timestamp>='2023-01-25 00:00:00' AND timestamp<'2023-01-26 00:00:00';")

# vn.train(question="How much cpu and memory was used on june 15th, 2023?",
#          sql="SELECT cpu_usage, memory_usage, timestamp FROM vmCloud_data WHERE timestamp>='2023-06-15 00:00:00' AND timestamp<'2023-06-16 00:00:00';")

# vn.train(question="How much cpu and memory was used on july 19th, 2023?",
#          sql="SELECT cpu_usage, memory_usage, timestamp FROM vmCloud_data WHERE timestamp>='2023-07-19 00:00:00' AND timestamp<'2023-07-20 00:00:00';")

# # vn.train(question=)

# training_data = vn.get_training_data()
# print(training_data)

# result = vn.ask(question="What was the server data from january 25th 2023?")
# print("###############################")
# print(result[1])

# training_data = vn.get_training_data()
# print(training_data.id)
# for id in training_data.id:
#     vn.remove_training_data(id)

# vn.remove_training_data('cdbbf0ee-4b4e-55b1-9ff7-61165d2f3b1b-sql')