from flask import Flask, jsonify, send_from_directory, Response, request
import clickhouse_connect
import pandas as pd
import vanna

from vanna.ollama import Ollama
from vanna.chromadb import ChromaDB_VectorStore

from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)

SWAGGER_URL = '/api/docs'
API_URL = '/static/swagger.json'
SWAGGER_BLUEPRINT = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name' : "Vanna API"
    }
)

app.register_blueprint(SWAGGER_BLUEPRINT, url_prefix = SWAGGER_URL)



class MyVanna(ChromaDB_VectorStore, Ollama):
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        Ollama.__init__(self, config=config)

vn = MyVanna(config={'model': 'llama3.1'})

vn.connect_to_clickhouse(host='by8y1h0mfc.us-west-2.aws.clickhouse.cloud',
                            dbname='default',
                            user='default',
                            password='u.XyyiQGvIUB2',
                            port=8443)


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/ask_question/json/<prompt>')
def ask_question_json(prompt):
    sql = vn.generate_sql(question=prompt)
    result = vn.run_sql(sql)

    return jsonify(result.to_dict(orient="records"))


@app.route('/ask_question/csv/<prompt>')
def ask_question_csv(prompt):
    sql = vn.generate_sql(question=prompt)
    result = vn.run_sql(sql)

    csv_data = result.to_csv(index=False)

    return Response(csv_data, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=data.csv"})

@app.route('/ask_question/<prompt>')
def ask_question(prompt):
    sql = vn.generate_sql(question=prompt)
    result = vn.run_sql(sql)

    as_csv = request.args.get("as_csv", "false").lower() == "true"

    if as_csv:
        csv_data = result.to_csv(index=False)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=data.csv"}
        )
    else:
        # Convert to JSON and return
        return jsonify(result.to_dict(orient="records"))


@app.route('/test/<prompt>')
def test(prompt):
    return {"return": prompt}