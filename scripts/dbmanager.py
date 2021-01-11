import MySQLdb as _MySQL


class Database:
    """A class that handles the database connection"""

    def __init__(self, host, user, password, db, **kwargs):
        """
        Constructor to initialize the connection

        Parameters:
            host     - The host name
            user     - The username
            password - The password
            db       - The databse name
            kwargs   - The rest optional arguments for the databse connection
        """
        self.host     = host
        self.user     = user
        self.password = password
        self.db       = db
        self.kwargs   = kwargs
        self.con      = None

    def open(self):
        """
        Opens the connection to the database

        Raises:
            RuntimeError - If already open
        """
        if self.con is not None:
            raise RuntimeError("Database already open")
        self.con  = _MySQL.connect( host=self.host,
                                    user=self.user,
                                    passwd=self.password,
                                    db=self.db,
                                    **self.kwargs)

    def close(self):
        """Closes the connection to the database"""
        if self.con is None:
            self.con.close()
            self.con = None

    def __enter__(self):
        """
        Executes open

        Returns:
            self
        """
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Execute close"""
        self.close()

    def statement(self, statement, values):
        """
        Executes the given statement with the given values

        Parameters:
            statement - The statetment to execute
            values    - The values or named values to replace to the statement

        Returns:
            A tuple with all the results of the statetment (if it was a query)
        """
        with self.con.cursor() as cursor:
            cursor.execute(statement, values)
            return cursor.fetchall()
    
    def commit(self):
        """Commits the changes to the database"""
        self.con.commit()
        
    def rollback(self):
        """Rollbacks any changes"""
        self.con.rollback()

    def createObject(self, name, cols="*"):
        """
        Creates an SQLObject

        Parameters:
            name - The name of the object
            cols - The columns of the object (Optional: defaults to '*')

        Returns:
            The SQLObject with this database as its connection
        """
        return SQLObject(db=self, name=name, cols=cols)



class SQLObject:
    """An SQLObject handles the statement creation and execution in an OOP manner"""

    def __init__(self, db, name=None, table=None, cols=None):
        """
        Constructs the object with the given parameters

        Parameters:
            db    - The connection
            name  - The name of the table         (Optional)
            table - The actual table of the query (Optional)
                        Overrides the name parameter
            cols  - The column names              (Optional: defaults to '*')

        Raises:
            TypeError - If both the name and the table are not set
            TypeError - If cols are not iterable
        """
        self.db = db

        if name is None and table is None:
            raise TypeError("name and table cannot be both none")
        elif table is None:
            table = name
        else:
            name = None

        self.name  = name
        self.table = table

        if cols is None:
            self.cols = "*"
        else:
            self.cols = tuple(f"{name}.{col}" if name else f"{col}" for col in cols)

    def query(self, cols=None, condition="", values=None):
        """
        Executes a query on the table

        Parameters:
            cols      - The column names                           (Optional: defaults to '*')
            condition - The condition of the query                 (Optional)
            values    - The values or named values of the query    (Optional)

        Returns:
            A tuple with all the items pulled by the database

        Raises:
            TypeError - If cols is not iterable
            TypeError - If values is not iterable
        """
        if cols is None:
            cols = self.cols
        elif not isinstance(cols, str):
            cols = tuple(c for c in cols)

        if values is not None and not isinstance(values, dict):
            values = tuple(v for v in values)

        statement = f"""SELECT {','.join(cols)} FROM {self.table} {condition}"""

        return self.db.statement(statement, values)

    def insert(self, values):
        """
        Executes an insertion on the table

        Parameters:
            values - The values or named values to insert

        Raises:
            TypeError  - If the table is not named (ex: join)
            TypeError  - If values are not dictionary or iterable
            ValueError - If the values are not named and not enough for the given self.cols
            ValueError - If the dictionary or iterable is empty
        """
        if self.name is None:
            raise TypeError("Cannot insert into nameless tables")
        if isinstance(values, dict):
            cols = tuple(values.keys())
            vals = tuple(values.values())
        else:
            cols = self.cols
            vals = tuple(v for v in values)
            if not isinstance(cols, str) and len(cols) != len(vals):
                raise ValueError("values do not have the same size as the default columns")

        if len(values) == 0:
            raise ValueError("values cannot be empty")

        strcols   = "" if cols == "*" else f"({','.join(cols)})"
        prevalues = f"""({'%s,'*(len(vals)-1)}%s)"""
        statement = f"""INSERT INTO {self.table} {strcols} VALUES {prevalues}"""

        self.db.statement(statement, vals)

    def join(self, other, on=None, type="INNER"):
        """
        Creates a JOIN table to execute queries on

        Parameters:
            other - The other SQLObject to join on
            on    - The on-expression
        """
        table = f"{self.table} {type} JOIN {other.table}" + ( f" ON {on}" if on else "" )

        if self.cols == "*":
            cols = other.cols
        elif other.cols == "*":
            cols = self.cols
        else:
            cols = (*self.cols, *other.cols)

        return SQLObject(self.db, table=table, cols=cols)
