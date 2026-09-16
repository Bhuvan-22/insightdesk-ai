# Running InsightDesk AI as a Web Application

## Local

```bash
python -m venv venv
# Windows
venv\Scripts\activate
pip install -r requirements.txt
streamlit run web_app.py
```

Open the local URL shown by Streamlit (normally http://localhost:8501).

## Public deployment

A simple option is Streamlit Community Cloud. Push this project to GitHub, create a new Streamlit app, select `web_app.py` as the main file, and deploy. Add `LLM_API_KEY` as a secret only if you have implemented a live provider in `src/llm/client.py`.

The app can run without a key using the project's built-in deterministic mock mode.
