# Coil Ranker Prototype

This project is a prototype options ranker designed to test the "Coil Hypothesis"—identifying option value based on the momentum decline of weekly candle ranges.

## Local Setup Instructions

Follow these steps to set up the project on your local machine and begin gathering intermediary data.

### 1. Clone the Repository
Clone the repository into a separate directory on your host machine:

```bash
git clone <your-repository-url> coil-ranker
cd coil-ranker
```

### 2. Environment Variables
The data gatherer relies on the Polygon API for historical OHLCV data. You must provide your API key.

Create a `.env` file in the root of the project:

```bash
touch .env
```

Open the `.env` file and add your Polygon API key:

```env
POLYGON_API_KEY=your_actual_api_key_here
```

### 3. Python Virtual Environment
Create and activate the virtual environment (macOS):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies
Once the virtual environment is active, install the required packages. You can install them via the `pyproject.toml` definition:

```bash
pip install --upgrade pip
pip install -e .
```

*(Note: If you encounter issues with `pyproject.toml`, the core requirements for the data gathering phase are `pandas`, `requests`, `polygon-api-client`, and `python-dotenv`).*

### 5. Run the Data Orchestrator
To begin pulling the 13-week historical data for the CBOE weeklies universe, run the orchestrator:

```bash
python src/build_intermediary_data.py
```

This will create a `data/raw/` directory and save individual CSVs for each ticker. The script is designed to be resilient—if you hit a rate limit or a network error, simply re-run the command; it will skip already downloaded tickers.
