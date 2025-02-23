from flask import Flask, request, jsonify, render_template
import requests
import traceback
import psycopg2

# Initialize Flask app
app = Flask(__name__)

# Configure PostgreSQL
POSTGRESQL_HOST = "localhost"
POSTGRESQL_DATABASE = "iot"
POSTGRESQL_USER = "postgres"
POSTGRESQL_PASSWORD = "123456"

# Configure Ollama API
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral:latest"

# Function to interact with Ollama
def query_ollama(user_message):
    prompt = f"Generate a suitable SQL query for the following request: '{user_message}'. Please ensure the table name matches the user's request accurately."
    ollama_response = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}, # stream: False means complete chunk
        headers={"Content-Type": "application/json"}
    )
    return ollama_response.json()

# Function to clean the SQL query
def clean_sql_query(query):
    # The goal is to extract a pure SQL query 
    start = query.find("```sql") + len("```sql") # we have to add 6 charachter of "```sql" because we dont want to add sql to the query and we loooking for pure Query
    end = query.find("```", start)
    clean_query = query[start:end].strip()  # Removes leading and trailing whitespace (spaces, tabs, newlines) from the extracted substring
    return clean_query

# Function to query PostgreSQL and get column names
def query_postgresql(query):
    try:
        conn = psycopg2.connect(
            host=POSTGRESQL_HOST,
            database=POSTGRESQL_DATABASE,
            user=POSTGRESQL_USER,
            password=POSTGRESQL_PASSWORD
        )
        cur = conn.cursor()
        
        # Execute the query
        cur.execute(query)
        results = cur.fetchall() # Fetches all rows from the query result.
        
        # Get column names
        colnames = [desc[0] for desc in cur.description] # cur.description Column name (first element, desc[0]).
        
        cur.close()
        conn.close()
        
        # Pair column names with their respective values
        detailed_results = [dict(zip(colnames, row)) for row in results]    # Converts the paired tuples into a dictionary =>  results = [(1, "Alice", 25),(2, "Bob", 30)] and colnames = ["id", "name", "age"] zip(colnames, row) -> [("id", 1), ("name", "Alice"), ("age", 25)]
        
        return detailed_results
    except Exception as e:
        print("Error querying PostgreSQL:", str(e))
        traceback.print_exc()
        return []

@app.route("/")
def index():
    return render_template("index2.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message") # Extracts the value of the "message" key from the JSON payload.
    
    try:
        print("User message:", user_message)  # Debugging user message
        
        # Interact with Ollama
        ollama_response_json = query_ollama(user_message) # send the user’s message to the Ollama API.
        print("Ollama response:", ollama_response_json)  # Debug line
        
        ollama_message = ollama_response_json.get("response", "") #Extracts the value of the "response" key from Ollama’s JSON response.
        
        # Extract and clean the query from Ollama's response
        sql_query = clean_sql_query(ollama_message)  #Calls the clean_sql_query() function to extract the SQL query from the markdown code block.
        print("Generated SQL query:", sql_query)  # Debug line
        
        # Execute the query on PostgreSQL and get detailed results
        query_results = query_postgresql(sql_query)
        
        # Return the results as JSON
        return jsonify({"results": query_results})

    except Exception as e:
        print("Error occurred:", str(e))
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
