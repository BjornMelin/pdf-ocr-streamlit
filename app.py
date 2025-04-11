import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import ollama
import io
import os
import base64
import time
from pathlib import Path

# --- Configuration ---
OLLAMA_MODEL = "gemma-3-4b-it-gpu:latest"
OUTPUT_DIR = "md_docs"
MAX_PROCESSING_TIME_PER_PAGE_SECONDS = 120  # Add a timeout per page

# --- Helper Functions ---


def render_pdf_page_as_image_bytes(
    pdf_bytes: bytes, page_num: int, zoom: int = 2
) -> bytes | None:
    """Renders a specific page of a PDF as PNG image bytes.

    Args:
        pdf_bytes: The content of the PDF file as bytes.
        page_num: The page number to render (0-indexed).
        zoom: The zoom factor for rendering (higher zoom = higher resolution).

    Returns:
        The PNG image data as bytes, or None if an error occurs.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if page_num >= len(doc):
            st.error(f"Error: Page number {page_num + 1} out of range for PDF.")
            return None

        page = doc.load_page(page_num)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()
        doc.close()
        return img_byte_arr
    except Exception as e:
        st.error(f"Error rendering PDF page {page_num + 1}: {e}")
        return None


def extract_text_from_image_bytes(
    image_bytes: bytes, model_name: str, page_num: int, filename: str
) -> str | None:
    """Extracts text from image bytes using a multimodal Ollama model.

    Args:
        image_bytes: The PNG image data as bytes.
        model_name: The name of the Ollama model to use (must be multimodal).
        page_num: The page number (for logging/error messages).
        filename: The original filename (for logging/error messages).

    Returns:
        The extracted text as a string, or None if an error occurs.
    """
    try:
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        prompt = "Extract all text content from this image accurately. Preserve the original structure and formatting as much as possible in Markdown format."
        messages = [{"role": "user", "content": prompt, "images": [b64_image]}]
        response = ollama.chat(
            model=model_name,
            messages=messages,
            options={"temperature": 0.1},
            keep_alive="-1m",
        )
        return response["message"]["content"]
    except ollama.ResponseError as e:
        st.error(
            f"Ollama API Error (Page {page_num + 1}, File '{filename}'): {e.error}"
        )
        st.warning(
            f"Ensure the Ollama server is running and the model '{model_name}' is pulled and is MULTIMODAL (can process images)."
        )
        return None
    except Exception as e:
        st.error(
            f"Error during text extraction (Page {page_num + 1}, File '{filename}'): {e}"
        )
        return None


def process_pdf(
    uploaded_file, model_name: str, output_dir: str, status_container
) -> tuple[bool, str | None]:
    """Processes a single uploaded PDF file for OCR.

    Args:
        uploaded_file: The Streamlit UploadedFile object.
        model_name: The Ollama model name.
        output_dir: The directory to save the output Markdown file.
        status_container: The Streamlit status container for progress updates.

    Returns:
        A tuple containing:
        - bool: True if processing was successful (even if partial), False otherwise.
        - str | None: The path to the generated Markdown file if successful, else None.
    """
    filename = uploaded_file.name
    status_container.write(f"📄 Starting processing for: **{filename}**")
    start_time_file = time.time()
    output_path = None  # Initialize output path
    processing_successful = True  # Assume success unless a critical error occurs
    partial_success = False  # Flag if some pages failed but others succeeded

    try:
        pdf_bytes = uploaded_file.getvalue()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        num_pages = len(doc)
        doc.close()

        if num_pages == 0:
            status_container.warning(f"⚠️ Skipping '{filename}': No pages found.")
            return False, None

        status_container.write(f"Total pages found: {num_pages}")

        all_pages_text = []
        page_progress = st.progress(0.0, text=f"Page 1/{num_pages}")

        for i in range(num_pages):
            page_num = i + 1
            status_container.write(f"    - Rendering Page {page_num}...")
            start_time_page = time.time()

            image_bytes = render_pdf_page_as_image_bytes(pdf_bytes, i)

            if image_bytes:
                status_container.write(
                    f"    - Extracting text from Page {page_num} using '{model_name}'..."
                )
                extracted_text = extract_text_from_image_bytes(
                    image_bytes, model_name, i, filename
                )

                if extracted_text:
                    all_pages_text.append(
                        f"## Page {page_num}\n\n{extracted_text}\n\n---\n"
                    )
                    status_container.write(
                        f"    ✅ Text extracted for Page {page_num}."
                    )
                else:
                    status_container.warning(
                        f"    ⚠️ Failed to extract text for Page {page_num}. Skipping page content."
                    )
                    all_pages_text.append(
                        f"## Page {page_num}\n\n[Text extraction failed for this page]\n\n---\n"
                    )
                    partial_success = True  # Mark as partial success

                elapsed_time_page = time.time() - start_time_page
                if elapsed_time_page > MAX_PROCESSING_TIME_PER_PAGE_SECONDS:
                    status_container.error(
                        f"    ❌ Timeout processing Page {page_num} after {elapsed_time_page:.1f}s. Stopping processing for this file."
                    )
                    processing_successful = False  # Mark as failed due to timeout
                    break  # Stop processing this file
            else:
                status_container.warning(
                    f"    ⚠️ Failed to render Page {page_num}. Skipping page content."
                )
                all_pages_text.append(
                    f"## Page {page_num}\n\n[Page rendering failed]\n\n---\n"
                )
                partial_success = True  # Mark as partial success

            progress_percentage = min(1.0, page_num / num_pages)
            page_progress.progress(
                progress_percentage, text=f"Page {page_num}/{num_pages}"
            )
            time.sleep(0.1)

        page_progress.empty()  # Remove progress bar for this file

        # --- File Saving ---
        if processing_successful and all_pages_text:
            output_filename = Path(output_dir) / f"{Path(filename).stem}.md"
            os.makedirs(output_dir, exist_ok=True)
            output_path = str(output_filename)

            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(f"# OCR Output for: {filename}\n\n")
                if partial_success:
                    f.write(
                        "**Note:** Text extraction or page rendering failed for one or more pages. The output may be incomplete.\n\n---\n\n"
                    )
                f.write("".join(all_pages_text))

            end_time_file = time.time()
            total_time_file = end_time_file - start_time_file
            status_message = "partially " if partial_success else ""
            status_container.write(
                f"✅ Successfully {status_message}processed '{filename}' in {total_time_file:.2f} seconds."
            )
            return True, output_path  # Return True if any output was generated
        elif not processing_successful:
            status_container.error(
                f"❌ Failed to process '{filename}' due to critical error (e.g., timeout)."
            )
            return False, None
        else:  # No text extracted at all, even without critical errors
            status_container.error(f"❌ No text could be extracted from '{filename}'.")
            return False, None

    except Exception as e:
        status_container.error(f"❌ Critical error processing '{filename}': {e}")
        if "page_progress" in locals():
            page_progress.empty()
        return False, None


# --- Streamlit UI ---

st.set_page_config(layout="wide")
st.title("📄 PDF OCR with Local Ollama Model")
st.markdown(
    f"""
Upload PDF files below. The app uses the local Ollama model **`{OLLAMA_MODEL}`** to extract text.
Click 'Start OCR Processing' once your files are uploaded.

**Important:** This app requires a **multimodal** Ollama model (like `llava`) capable of processing images.
If `{OLLAMA_MODEL}` is text-only, text extraction will fail. Ensure the correct model is running in Ollama.
"""
)

# --- File Uploader ---
# This widget now handles displaying the list of files and allows removal via 'x'
uploaded_files = st.file_uploader(
    "Choose PDF files", type="pdf", accept_multiple_files=True, key="file_uploader"
)


# --- Processing Button and Logic ---
st.divider()
start_processing = st.button(
    "🚀 Start OCR Processing",
    # Disable button if no files are currently listed in the uploader
    disabled=not uploaded_files,
    type="primary",
)

if start_processing and uploaded_files:
    st.subheader("⚙️ Processing Files...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    results_summary = []
    overall_start_time = time.time()

    # Use the list of files directly from the uploader
    files_to_process = uploaded_files

    with st.status(
        f"Starting OCR for {len(files_to_process)} file(s)...", expanded=True
    ) as status:
        for i, uploaded_file in enumerate(files_to_process):
            # Create a temporary container within the status for this file's logs
            # file_status_container = st.container() # Use container if needed for more structure
            status.update(
                label=f"Processing file {i+1}/{len(files_to_process)}: **{uploaded_file.name}**"
            )
            # Pass the main status object for updates
            success, output_path = process_pdf(
                uploaded_file, OLLAMA_MODEL, OUTPUT_DIR, status
            )
            results_summary.append(
                {
                    "filename": uploaded_file.name,
                    "success": success,
                    "output_path": output_path,
                }
            )
            time.sleep(0.5)  # Small delay between files

        overall_end_time = time.time()
        total_processing_time = overall_end_time - overall_start_time
        status.update(
            label=f"✅ Processing Complete! ({total_processing_time:.2f}s)",
            state="complete",
            expanded=False,
        )

    # --- Display Summary ---
    st.subheader("📊 Processing Summary")
    successful_files = [r for r in results_summary if r["success"]]
    failed_files = [r for r in results_summary if not r["success"]]

    if successful_files:
        st.success(f"**Successfully processed {len(successful_files)} file(s):**")
        for result in successful_files:
            # Added icon and clearer path indication
            st.markdown(
                f"✔️ **{result['filename']}** → Output saved to `{result['output_path']}`"
            )
    else:
        st.info("No files were processed successfully.")

    if failed_files:
        st.error(f"**Failed or could not process {len(failed_files)} file(s):**")
        for result in failed_files:
            # Added icon
            st.markdown(
                f"❌ **{result['filename']}** (Check logs in the collapsed 'Processing Complete' section above for details)"
            )

    st.info(f"Total processing time: {total_processing_time:.2f} seconds.")
