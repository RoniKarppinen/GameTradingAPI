# PWP SPRING 2026
# Game Trading API

## Project layout

```text
├── README.md               # Documentation
├── pyproject.toml          # Project configuration and dependencies
├── GameTrading                     
│   ├── app.py              # Main API logic
│   ├── db.py               # Main database logic
│   └── populate.py         # Populate the database with synthetic data
└── tests
    ├── test_app.py         # Test the API logic
    ├── test_populate.py    # Test populate logic
    └── test_db.py          # Test database logic
```

## Libraries used

- Flask
- Flask-RESTful
- Flask-SQLAlchemy
- jsonschema
- pytest
- pytest-cov
- pylint

## Setup & installation
1. Install Dependencies:
```
pip install ".[dev]"
```

2. Database setup:
* Create the database structure: Run db.py to initialize the database.

```
python GameTrading/db.py
```

* Run populate.py to add sample users, games and trades
```
python -m GameTrading.populate
```

3. Running the API:
* Run the following commands in the root directory to open the server

```
cd GameTrading
```

```
flask run
```

4. Running tests
* Run the following command in the root directory to run the tests and see the coverage.

**Run this only if you are inside directory "GameTrading/"**
```
cd ..
```


Then run this


```
python -m pytest
```

5. Running pylint
* Run the following command from the root directory
```
python -m pylint GameTrading tests
```

## API entry point URL

Currently the API is not deployed remotely anywhere.


The base URL for accesing the API locally:
'http://127.0.0.1:5000/api/'

Primary entry points:
* **User Registration:** `POST http://127.0.0.1:5000/api/users/`
* **Game Hub:** `GET http://127.0.0.1:5000/api/games/`

## Database info
* Database: SQLite version: 3.50.4
* ORM: Flask-SQLAlchemy

# Group information
* Student 1. Roni Karppinen, Roni.Karppinen@student.oulu.fi
* Student 2. Luan Trieu, Luan.Trieu@student.oulu.fi
* Student 3. Minttu Ukkola, Minttu.Ukkola@student.oulu.fi


__Remember to include all required documentation and HOWTOs, including how to create and populate the database, how to run and test the API, the url to the entrypoint, instructions on how to setup and run the client, instructions on how to setup and run the axiliary service and instructions on how to deploy the api in a production environment__

