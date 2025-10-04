import os
import mysql.connector
from mysql.connector import errorcode
from dotenv import load_dotenv

def setup_database():
    """
    Connects to MySQL, creates the database if it doesn't exist,
    and then creates the necessary tables by executing SQL files.
    """
    # Load environment variables from the root .env file
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)

    db_host = os.getenv("MYSQL_HOST")
    db_user = os.getenv("MYSQL_USER")
    db_password = os.getenv("MYSQL_PASSWORD")
    db_name = os.getenv("MYSQL_DB")

    try:
        # 1. Connect to MySQL server to create the database
        print(f"Connecting to MySQL server at {db_host}...")
        cnx = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password
        )
        cursor = cnx.cursor()
        print(f"Creating database '{db_name}' if it does not exist...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET 'utf8mb4'")
        cursor.close()
        cnx.close()

        # 2. Connect to the specific database to create tables
        print(f"Connecting to database '{db_name}'...")
        cnx = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name
        )
        cursor = cnx.cursor()

        # 3. Find and execute SQL schema files
        schema_dir = os.path.join(os.path.dirname(__file__), 'schemas')
        sql_files = sorted([f for f in os.listdir(schema_dir) if f.endswith('.sql')])

        if not sql_files:
            print(f"No .sql files found in {schema_dir}. No tables created.")
            return

        for sql_file in sql_files:
            print(f"Executing {sql_file}...")
            with open(os.path.join(schema_dir, sql_file), 'r') as f:
                sql_script = f.read()
                # Split the script into individual statements and execute each
                statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
                for statement in statements:
                    cursor.execute(statement)

        print("\nDatabase setup complete. All tables created successfully.")

    except mysql.connector.Error as err:
        print(f"Failed to set up database: {err}")
    finally:
        if 'cnx' in locals() and cnx.is_connected():
            cursor.close()
            cnx.close()
            print("MySQL connection closed.")

if __name__ == "__main__":
    setup_database()