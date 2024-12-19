import ollama
import vanna as vn
import pandas as pd
import ollama
import clickhouse_connect
import clickhouse_driver
from vanna.base import VannaBase

# emb = ollama.embeddings(model="llama3.2", prompt="This is the test of all tests")['embedding']

# print(emb)

vn = VannaBase()

vn.connect_to_clickhouse(host='by8y1h0mfc.us-west-2.aws.clickhouse.cloud',
                            dbname='default',
                            user='default',
                            password='u.XyyiQGvIUB2',
                            port=8443)

ddl_input = "CREATE TABLE IF NOT EXISTS vmCloud_data (vm_id String, timestamp DateTime, cpu_usage Float64, memory_usage Float64, network_traffic Float64, power_consumption Float64, num_executed_instructions Float64, execution_time Float64, energy_efficiency Float64, task_type String, task_priority String)"

df_information_schema = vn.run_sql("SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'vmCloud_data'")
# print(df_information_schema)

plan = vn.get_training_plan_generic(df_information_schema)

print(plan)

vn.train(plan=plan)

vn.train(ddl=ddl_input)

vn.train(documentation="Our data defines vm cloud server data that includes cpu usage, memory usage, network traffic, power consumption, instructions executed, execution time, energy efficiency, task type, task priority, and task status.")

vn.train(question="What is the server data from january 25th, 2023?",
         sql="SELECT * FROM vmCloud_data WHERE timestamp>='2023-01-25 00:00:00' AND timestamp<'2023-01-26 00:00:00';")

vn.train(question="How much cpu and memory was used on june 15th, 2023?",
         sql="SELECT cpu_usage, memory_usage, timestamp FROM vmCloud_data WHERE timestamp>='2023-06-15 00:00:00' AND timestamp<'2023-06-16 00:00:00';")

vn.train(question="How much cpu and memory was used on july 19th, 2023?",
         sql="SELECT cpu_usage, memory_usage, timestamp FROM vmCloud_data WHERE timestamp>='2023-07-19 00:00:00' AND timestamp<'2023-07-20 00:00:00';")

vn.ask("What is the server data from january 25th, 2023?")