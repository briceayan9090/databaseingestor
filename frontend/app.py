import streamlit as st
import pandas as pd
import psycopg2
import os
import re

print('Streamlit app started')
# --- Database Connection Details ---
DB_HOST = os.environ.get("DB_HOST", "db")
DB_NAME = os.environ.get("DB_NAME", "mydatabase")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")

st.title("XLSX Ingestor")

uploaded_files = st.file_uploader("Upload one or more XLSX files", type=["xlsx"], accept_multiple_files=True)

def sanitize_column_name(name):
    """Removes or replaces invalid characters from a column name."""
    # Replace '#' with an underscore, remove other non-alphanumeric characters (except underscore),
    # and ensure it starts with a letter or underscore
    name = re.sub(r'[^a-zA-Z0-9_]', '_', str(name))
    name = re.sub(r'^[^a-zA-Z_]+', '', name)
    name = name.lower()
    reserved_keywords = ["from", "to", "user", "group", "order", "by", "select", "insert", "update", "delete", "create", "table", "view", "grant", "revoke", "alter", "column", "constraint", "index", "function", "procedure"]  # Add more if needed
    if name in reserved_keywords:
        name = f"_{name}"
    return name

# --- Optional: User-Defined Type Overrides ---
type_overrides = {}
if uploaded_files:
    first_file = uploaded_files[0]
    try:
        all_sheets_preview = pd.read_excel(first_file, sheet_name=None, nrows=1, header=0)  # Header is row 1
        for sheet_name, df_preview in all_sheets_preview.items():
            for original_col in df_preview.columns:
                sanitized_col = sanitize_column_name(original_col)
                type_overrides[f"{sheet_name}.{sanitized_col}"] = st.selectbox(
                    f"Override type for '{sheet_name}.{sanitized_col}' (Leave as 'Auto' for automatic inference):",
                    ["Auto", "SMALLINT", "INTEGER", "BIGINT", "REAL", "DOUBLE PRECISION", "DATE", "TIMESTAMP", "BOOLEAN", "VARCHAR(255)", "TEXT", "NUMERIC"],
                    key=f"type_override_{sheet_name}_{sanitized_col}"
                )
    except Exception as e:
        st.warning(f"Could not preview columns for type overrides: {e}")

def get_postgres_type(pandas_dtype, series, override_type):
    """Maps pandas dtype to a more specific PostgreSQL type with potential override."""
    if override_type != "Auto":
        return override_type

    if pandas_dtype == 'object':
        return "TEXT"  # Force all 'object' columns to TEXT

    if pd.api.types.is_integer_dtype(pandas_dtype) or pd.api.types.is_float_dtype(pandas_dtype):
        try:
            pd.to_numeric(series, errors='raise')
            if pd.api.types.is_integer_dtype(pandas_dtype):
                min_val = series.min() if not series.empty else 0
                max_val = series.max() if not series.empty else 0
                if -32768 <= min_val and max_val <= 32767:
                    return "SMALLINT"
                elif -2147483648 <= min_val and max_val <= 2147483647:
                    return "INTEGER"
                else:
                    return "BIGINT"
            elif pd.api.types.is_float_dtype(pandas_dtype):
                return "DOUBLE PRECISION"
        except ValueError:
            return "TEXT"
        except TypeError:
            return "TEXT"
    elif pd.api.types.is_datetime64_any_dtype(pandas_dtype):
        if series.dt.time.nunique() == 1 and series.dt.time.iloc[0].hour == 0 and series.dt.time.iloc[0].minute == 0 and series.dt.time.iloc[0].second == 0 and series.dt.time.iloc[0].microsecond == 0:
            return "DATE"
        else:
            return "TIMESTAMP"
    elif pd.api.types.is_bool_dtype(pandas_dtype):
        return "BOOLEAN"
    else:
        return "TEXT"

def create_table_if_not_exists(conn, table_name, df):
    cur = conn.cursor()
    columns_definition = []
    sanitized_columns = [sanitize_column_name(col) for col in df.columns]
    print(f"Table: {table_name}, Sanitized Columns: {sanitized_columns}")  # Log sanitized column names
    for original_col, sanitized_col in zip(df.columns, sanitized_columns):
        override_key = f"{table_name}.{sanitized_col}"
        override_type = type_overrides.get(override_key, "Auto")
        postgres_type = get_postgres_type(df[original_col].dtype, df[original_col], override_type)
        nullable = "NULL" if df[original_col].isnull().any() else "NOT NULL"
        columns_definition.append(f"{sanitized_col} {postgres_type} {nullable}")

    columns_str = ", ".join(columns_definition)
    create_table_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        {columns_str}
    );
    """
    print(f"CREATE TABLE Query for {table_name}: {create_table_query}")  # Log the CREATE TABLE query
    try:
        cur.execute(create_table_query)
        conn.commit()
        st.info(f"Table '{table_name}' created successfully with sanitized column names.")
    except psycopg2.Error as e:
        st.error(f"Error creating table '{table_name}': {e}")
        conn.rollback()

def insert_dataframe_to_table(conn, table_name, df):
    cur = conn.cursor()
    sanitized_columns = [sanitize_column_name(col) for col in df.columns]
    columns_str = ', '.join(sanitized_columns)
    placeholders = ', '.join(['%s'] * len(df.columns))
    insert_query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders});"

    print(f"First 5 rows of DataFrame '{table_name}':")  # Log first few rows
    print(df.head().to_string())

    for index, row in df.iterrows():
        row_values = row.values.tolist()
        cleaned_row_values = [None if pd.isna(val) else val for val in row_values]
        try:
            cur.execute(insert_query, cleaned_row_values)
        except psycopg2.Error as e:
            st.error(f"Error inserting row into '{table_name}': {cleaned_row_values} - {e}")
            print(f"Error details: {e}")  # Print full error details
            conn.rollback()  # Rollback on error for the current row
            break  # Break the loop after the first error for easier debugging
    conn.commit()  # Commit after all rows are attempted
    st.success(f"Data from sheet '{table_name}' inserted into table '{table_name}' successfully.")

def get_table_names_from_db():
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        cur = conn.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        table_names = [row[0] for row in cur.fetchall()]
        return table_names
    except psycopg2.Error as e:
        st.error(f"Error fetching table names: {e}")
        return []
    finally:
        if conn:
            conn.close()

if uploaded_files:
    ingest_button = st.button("Ingest Data")  # Moved button to the top
    print(f"Ingest Button State (after creation): {ingest_button}")  # Log initial button state

    if ingest_button:
        print("Ingest Data button was clicked!")  # Confirm button click
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT
            )
            print("Successfully connected to the database (inside if ingest_button)")  # Confirm database connection
            for uploaded_file in uploaded_files:
                print(f"Starting processing file: {uploaded_file.name}")  # Log file processing start
                st.subheader(f"Processing file: {uploaded_file.name}")
                try:
                    print(f"Attempting to read all sheets from {uploaded_file.name}")  # Log before reading file
                    all_sheets = pd.read_excel(uploaded_file, sheet_name=None, header=0)  # Start reading data from row 1(header is row 1)
                    print(f"Successfully read all sheets from {uploaded_file.name}")  # Log after reading file
                    for sheet_name, df in all_sheets.items():
                        print(f"Starting processing sheet: {sheet_name}")  # Log sheet processing start
                        if not df.empty:
                            table_name = sanitize_column_name(sheet_name)  # Sanitize sheet name for table name
                            st.info(f"Processing sheet: '{sheet_name}' and attempting to create/insert into table '{table_name}'")
                            create_table_if_not_exists(conn, table_name, df)  # Uncommented
                            insert_dataframe_to_table(conn, table_name, df)  # Uncommented
                            print(f"Processed sheet '{sheet_name}'")  # Updated log
                        else:
                            st.warning(f"Sheet '{sheet_name}' in '{uploaded_file.name}' is empty.")
                        print(f"Finished processing sheet: {sheet_name}")  # Log inner loop end
                except Exception as e:
                    st.error(f"Error reading file '{uploaded_file.name}': {e}")
                    print(f"Error reading file: {e}")  # Log the specific file reading error
                print(f"Finished processing file: {uploaded_file.name}")  # Log outer loop end
            conn.close()
            print("Data ingestion process completed (inside if ingest_button)")  # Confirm completion
            st.info("Data ingestion process completed for all files.")

        except psycopg2.Error as e:
            print(f"Error connecting to database (inside if ingest_button): {e}")  # Log database connection error
            st.error(f"Error connecting to database: {e}")
else:
    st.warning("Please upload one or more XLSX files.")

st.markdown("---")
st.subheader("View Data from a Table:")

table_names = get_table_names_from_db()
if table_names:
    selected_table = st.selectbox("Select a table to view data:", table_names)
    if selected_table:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT
            )
            cur = conn.cursor()
            try:
                cur.execute(f"SELECT * FROM {selected_table} LIMIT 30;")
                data = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
                conn.close()
                if data:
                    st.dataframe(pd.DataFrame(data, columns=columns))
                else:
                    st.info(f"Table '{selected_table}' is empty.")
            except psycopg2.Error as e:
                st.error(f"Error fetching data from table '{selected_table}': {e}")
        except psycopg2.Error as e:
            st.error(f"Error connecting to database to view data: {e}")
else:
    st.info("No tables found in the database.")