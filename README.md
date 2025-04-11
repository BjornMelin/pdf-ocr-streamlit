# PDF OCR with Streamlit and Local Ollama

This application provides a web interface using Streamlit to upload PDF files and perform Optical Character Recognition (OCR) using a locally running Ollama multimodal language model. The extracted text is saved as Markdown files.

## Features

- Upload multiple PDF files.
- View and remove uploaded files before processing.
- Initiate OCR processing with a button click.
- Uses PyMuPDF (fitz) to render PDF pages as images.
- Uses Pillow to handle image data.
- Interacts with a local Ollama instance via the `ollama` library.
- **Requires a multimodal Ollama model** (e.g., `llava`) capable of processing images.
- Displays detailed progress during processing using `st.status`.
- Saves extracted text as Markdown files in the `md_docs` directory.
- Shows a summary of processed files.
- Project dependencies managed by `uv` via `pyproject.toml`.

## Prerequisites

1. **Python:** Version 3.9 or higher.
2. **uv:** The Python package installer and virtual environment manager. Install it if you haven't:

    ```bash
    pip install uv
    # or using pipx
    # pipx install uv
    ```

3. **Ollama:** Must be installed and running. You can download it from [https://ollama.com/](https://ollama.com/).
4. **Multimodal Ollama Model:** You need a model that can process images. Pull one using the Ollama CLI, for example:

    ```bash
    ollama pull llava:latest
    ```

    *Make sure the `OLLAMA_MODEL` constant in `app.py` matches the name of the multimodal model you want to use.* The default `gemma-3-4b-it-gpu:latest` is likely **text-only** and **will not work** for image-based OCR unless it's a specifically multimodal variant.

## Setup

1. **Clone the repository (or create the files):**

    ```bash
    # git clone <your-repo-url> # If you put it on GitHub
    # cd pdf-ocr-streamlit
    # Otherwise, just create the directory and files as described above.
    ```

2. **Create and activate the virtual environment using uv:**

    ```bash
    cd pdf-ocr-streamlit
    uv venv # Creates .venv
    source .venv/bin/activate # Linux/macOS
    # .\.venv\Scripts\activate # Windows (cmd/powershell)
    ```

3. **Install dependencies using uv:**

    ```bash
    uv pip install -r requirements.txt # uv can read requirements.txt format too
    # OR directly from pyproject.toml
    uv pip install .
    ```

## Running the Application

1. **Ensure Ollama is running** with the required multimodal model available.
2. **Run the Streamlit app:**

    ```bash
    streamlit run app.py
    ```

3. Open your web browser and navigate to the local URL provided by Streamlit (usually `http://localhost:8501`).

## Usage

1. Click "Browse files" or drag and drop PDF files onto the file uploader.
2. The uploaded files will appear in the "Files Ready for Processing" list.
3. You can remove files from the list by clicking the "Remove" button next to them.
4. Once you have the desired files listed, click the "🚀 Start OCR Processing" button.
5. The application will show detailed progress for each file and page.
6. Upon completion, a summary will be displayed, and the extracted Markdown files will be saved in the `md_docs` directory within the project folder.

## Future Enhancements (Ideas)

- Support for other file types (Word Docs, Images). This would require different libraries for rendering/parsing (e.g., `python-docx`, `Pillow` directly for images).
- More sophisticated error handling and reporting.
- Option to choose the Ollama model from the UI.
- Adjustable zoom/resolution for PDF rendering.
- Option to download the generated Markdown files directly from the UI.
- Batch processing improvements (e.g., parallel processing if Ollama/hardware supports it).
