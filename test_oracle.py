
import os
import oracledb

username = os.environ["ORACLE_USER"]
password = os.environ["ORACLE_PASSWORD"]
dsn = os.environ["ORACLE_DSN"]

try:
    connection = oracledb.connect(
        user=username,
        password=password,
        dsn=dsn
    )

    cursor = connection.cursor()
    cursor.execute("SELECT USER FROM DUAL")

    print("Connected to Oracle successfully!")
    print("Connected user:", cursor.fetchone()[0])

    cursor.close()
    connection.close()

except Exception as error:
    print("Connection failed:")
    print(error)
