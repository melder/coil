# Coil Ranker Prototype

This project is a prototype options ranker designed to test the "Coil Hypothesis"—identifying option value based on the momentum decline of weekly candle ranges.

## Local Setup Instructions

### 1. Clone the Repository
Clone the repository into a separate directory on your host machine:

```bash
git clone <your-repository-url> coil-ranker
cd coil-ranker
```

### 2. Environment Variables
The project relies on Polygon and Robinhood APIs. Create a `.env` file in the root of the project:

```env
# Polygon API (Historical OHLCV)
POLYGON_API_KEY=your_actual_api_key_here

# Robinhood API (Implied Volatility)
RH_USERNAME=your_email
RH_PASSWORD=your_password
RH_2FA_SECRET=your_actual_base32_secret
```

### 3. Python Virtual Environment
Ensure you have Python 3.14.5 installed. On macOS, you can use `pyenv`:

```bash
pyenv install 3.14.5
pyenv local 3.14.5
```

Create and activate the virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies
Once the virtual environment is active, install the required packages via the `pyproject.toml` definition:

```bash
pip install --upgrade pip
pip install -e .
```
