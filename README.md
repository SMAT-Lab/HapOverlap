# HapOverlap

A comprehensive framework for detecting and analyzing high-cost component overlap issues in mobile applications using AI-powered annotation and human validation.

## Overview

HapOverlap is designed to identify performance-critical UI issues where high-cost rendering components (such as videos, maps, animations, or complex charts) are significantly obscured by other UI elements. This can lead to unnecessary resource consumption and poor user experience.

## Project Structure

```
HapOverlap/
├── AnnotationWeb/          # Human annotation web platform
├── run_annotate/           # LLM detection scripts for high-cost overlap
├── anno_human_ai/          # Detection results from various AI models
├── Dataset/                 # Complete dataset of UI screenshots
└── Benchmark/              # Subset of data used for testing and evaluation
```

## Components

### 1. AnnotationWeb
A Flask-based web application that provides a user-friendly interface for human annotators to validate AI-generated overlap detections.

**Features:**
- Interactive UI for viewing before/current/after screenshots
- Side-by-side comparison of AI predictions and human annotations
- Support for multiple annotation categories
- Real-time annotation saving and validation

**Files:**
- `app.py` - Main Flask application
- `templates/` - HTML templates for the web interface
- `static/` - CSS and JavaScript files
- `requirements.txt` - Python dependencies

**Usage:**
```bash
cd AnnotationWeb
pip install -r requirements.txt
python app.py
```

### 2. run_annotate
A collection of Python scripts that use Large Language Models (LLMs) to automatically detect high-cost component overlap issues.

**Supported Models:**
- OpenAI GPT-4o-mini
- Qwen 2.5 VL 72B
- Llama 4 Maverick
- Gemini 2.5 Flash/Pro

**Key Scripts:**
- `en_auto_annotate_three.py` - Main annotation script with multi-model support
- `auto_annotate_gemini.py` - Gemini-specific annotation script
- `auto_annotate_aistudio.py` - AI Studio integration
- `merge_ai_human.py` - Merge AI and human annotations
- `eval_benchmark.py` - Evaluate annotation quality
- `make_benchmark.py` - Create benchmark datasets

**Usage:**
```bash
cd run_annotate
python en_auto_annotate_three.py --model openai --input_dir ../Dataset
```

### 3. anno_human_ai
Contains the detection results from various AI models, organized by model type.

**Files:**
- `gemini.json` - Gemini model annotations
- `openai.json` - OpenAI model annotations
- `qwen.json` - Qwen model annotations
- `llama.json` - Llama model annotations

### 4. Dataset
The complete collection of UI screenshots and visualizations used for training and evaluation.

**Structure:**
- Organized by application name
- Each sample contains before/current/after screenshots
- Supports various image formats (PNG, JPG, JPEG)

### 5. Benchmark
A curated subset of the dataset used for testing and evaluating model performance.

**Files:**
- `benchmark_full.json` - Complete benchmark dataset
- `benchmark_false.json` - False positive cases
- `benchmark_stat.json` - Statistical analysis results

## High-Cost Component Definition

The system identifies the following as high-cost components:

**Heavy Rendering:**
- Video players
- Complex animations
- Maps and location services
- Camera previews
- Long image lists
- WebViews

**Heavy Computation/IO:**
- Real-time refreshing charts
- Data-heavy lists with frequent updates
- Components requiring continuous processing

## Annotation Process

1. **AI Detection**: LLMs analyze screenshots to identify potential overlap issues
2. **Human Validation**: Annotators review AI predictions through the web interface
3. **Quality Control**: Benchmark evaluation ensures annotation accuracy
4. **Result Merging**: AI and human annotations are combined for final analysis

## Installation

### Prerequisites
- Python 3.8+
- Flask
- OpenAI API key (for OpenAI models)
- OpenRouter API key (for other models)

### Security Note
⚠️ **Important**: Never commit API keys to version control. The project includes placeholder values in the code and a separate configuration file for your actual keys.

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd HapOverlap

# Install dependencies
pip install -r AnnotationWeb/requirements.txt

# Configure API keys
cp config.example.py config.py
# Edit config.py with your actual API keys
```

## Usage

### 1. Run AI Annotation
```bash
cd run_annotate
python en_auto_annotate_three.py --model gemini --input_dir ../Dataset
```

### 2. Start Human Annotation Platform
```bash
cd AnnotationWeb
python app.py
```

### 3. Evaluate Results
```bash
cd run_annotate
python eval_benchmark.py --benchmark ../Benchmark/benchmark_full.json
```

## Configuration

### API Key Configuration
1. Copy the example configuration file:
   ```bash
   cp config.example.py config.py
   ```
2. Edit `config.py` with your actual API keys:
   - `OPENROUTER_API_KEY`: For OpenAI, Qwen, and Llama models
   - `GOOGLE_API_KEY`: For Gemini models
   - `OPENAI_API_KEY`: For direct OpenAI API access
   - `AI_STUDIO_API_KEY`: For AI Studio integration

### Model Configuration
Edit `run_annotate/en_auto_annotate_three.py` to configure:
- API endpoints
- Model parameters
- Input/output directories
- Annotation categories

### Web Interface Configuration
Modify `AnnotationWeb/app.py` to customize:
- Image data directory
- Annotation file paths
- UI labels and options
- Pagination settings

## Output Format

Annotations are stored in JSON format with the following structure:
```json
{
  "app_name": {
    "sample_id": {
      "ai": {
        "label": "Yes/No",
        "reason": "Explanation",
        "solution": "Optimization suggestions"
      },
      "human": {
        "label": "Yes/No",
        "annotator": "Human"
      }
    }
  }
}
```

