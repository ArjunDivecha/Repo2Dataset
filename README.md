# 🤖 gh-chat-dataset: Turn Any GitHub Repo into AI Training Data

**One-click tool to convert GitHub repositories into high-quality chat datasets for fine-tuning language models like Qwen with MLX.**

> 💡 **Perfect for**: Training coding assistants, documentation bots, or domain-specific AI models from real codebases.

**NEW**: Now includes a web-based UI for easy dataset generation! 🌐

## 🎯 What Does This Do?

This tool automatically extracts meaningful code-documentation pairs from GitHub repositories and formats them as conversation data that AI models can learn from.

**Think of it as**: Taking a repository full of Python functions with docstrings, JavaScript with JSDoc comments, and README files, then converting them into "teacher-student" conversations for AI training.

### 🧠 The Magic Behind It

- **Python Functions** → "Write a docstring for this function" conversations
- **JavaScript/TypeScript** → "Add JSDoc comments to this code" examples
- **Markdown Documentation** → "Explain this section" Q&A pairs
- **Smart Processing** → Removes duplicates, filters by length, splits for training

## 🚀 Quick Start (3 Minutes)

### Step 1: Install
```bash
# Clone this repository
git clone https://github.com/ArjunDivecha/Repo2Dataset.git
cd Repo2Dataset

# Install the tool
pip install -e .[dev]
```

### Step 2: Convert a Repository

```bash
# Example: Convert the popular 'requests' library into training data
gh-chat-dataset --repo https://github.com/psf/requests.git --out ./requests_dataset

# Or try a smaller example first
gh-chat-dataset --repo https://github.com/pallets/itsdangerous.git --out ./test_dataset
```

### Step 3: Check Your Results

```bash
ls test_dataset/
# You'll see:
# dataset.train.jsonl  <- 90% of samples for training
# dataset.valid.jsonl  <- 10% of samples for validation
# stats.json          <- Summary of what was extracted
```

## 📱 Calculator Demo

This repository includes a robust web-based calculator application built with Flask that you can try out locally:

### Running the Calculator

```bash
# Option 1: Using the installed command
calculator-app

# Option 2: Run directly with Flask
cd src/calculator_app
python -m flask run --host=0.0.0.0 --port=5000

# Option 3: Run the app.py file directly
python src/calculator_app/app.py
```

Then open your browser and navigate to:
```
http://localhost:5000
```

### Features

- **Basic Operations**: Addition (+), Subtraction (−), Multiplication (×), Division (÷)
- **Advanced Functions**: Percentage (%), Sign toggle (±), Backspace
- **Keyboard Support**: Use keyboard keys for all operations
- **Error Handling**: Handles division by zero and overflow errors gracefully
- **Smart Display**: Shows expression history and current value
- **Responsive Design**: Works beautifully on desktop and mobile

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| 0-9 | Enter number |
| +, -, *, / | Operations |
| Enter or = | Calculate result |
| Escape or C | Clear calculator |
| Backspace | Delete last digit |
| . | Decimal point |
| % | Percentage |

## 🌐 Web UI

This repository also includes a **full-featured web-based front-end** for generating datasets through a user-friendly interface. Perfect if you prefer a visual UI over the command line!

### Running the Web Application

```bash
# Ensure dependencies are installed
pip install -e .[web]

# Start the web server
gh-chat-dataset-web --port 5001

# With custom output directory
gh-chat-dataset-web --port 5001 --output-root ./my_outputs
```

Then open your browser and navigate to:
```
http://localhost:5001
```

### Web UI Features

- **Interactive Form**: Easy-to-use interface for all configurations
- **Real-time Progress**: Live status updates and progress bar
- **Live Logs**: View detailed logs as your dataset is being generated
- **Download Links**: One-click downloads for all output files
- **Advanced Options**: Full parity with CLI options for fine-tuning control
- **Job Management**: Run multiple jobs and track their status

### Configuration Options

The web UI supports all the same options as the CLI:

| Option | Description | Default |
|--------|-------------|---------|
| **GitHub Repository URL** | The repository to process (required) | - |
| **Output Name** | Custom name for output directory | Auto-generated |
| **Enable LLM-assisted labeling** | Use AI to generate labels (experimental) | OFF |
| **Max Tokens** | Maximum tokens per sample | 4096 |
| **Min Tokens** | Minimum tokens per sample | 48 |
| **Max Samples per File** | Limit samples per source file | 15 |
| **Max Questions/Section** | Q&A pairs per Markdown section | 4 |
| **Window Tokens** | Context window for Markdown processing | 800 |
| **Enable Python Chunking** | Split long Python functions | ON |
| **Max Chunks** | Maximum chunks per function | 5 |
| **Min Lines/Chunk** | Minimum lines per chunk | 6 |
| **Included Summaries** | Validation, Errors, Config, Logging | All ON |

### Using the Web UI

1. **Enter Repository URL**: Paste a GitHub repository URL (e.g., `https://github.com/psf/requests.git`)

2. **Configure Options**:
   - Leave defaults for quick start
   - Expand "Advanced Options" for fine-tuning

3. **Click "Start Generation"**:
   - Watch real-time progress updates
   - View detailed logs in the logs panel

4. **Download Results**:
   - When complete, see sample counts and statistics
   - Download `dataset.train.jsonl`, `dataset.valid.jsonl`, and `stats.json`

### Output Files

Files are saved to the configured output directory (default: `./outputs/`):
```
outputs/
└── repo_name_20240101_143022/
    ├── dataset.train.jsonl   # Training samples (90%)
    ├── dataset.valid.jsonl   # Validation samples (10%)
    └── stats.json            # Summary statistics
```

### Production Deployment

For production use, you can serve the web app with a production WSGI server:

```bash
# Using gunicorn (install with: pip install gunicorn)
gunicorn -w 4 -b 0.0.0.0:5001 gh_chat_dataset.webapp.server:app

# With custom settings
REPO2DATASET_OUTPUT_ROOT=/data/datasets gunicorn -w 4 -b 0.0.0.0:5001 gh_chat_dataset.webapp.server:app
```

## 📊 Real Example Output

Let's say you run it on a Python repository. Here's what one training sample looks like:

**Input** (what the AI sees):
```
Write a clear, concise docstring for this function:

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
    return re.match(pattern, email) is not None
```

**Expected Output** (what the AI should respond):
```
Validate if an email address has a proper format.

Args:
    email (str): The email address to validate.

Returns:
    bool: True if email format is valid, False otherwise.
```

This creates training data that teaches AI models to write good documentation!

## ⚙️ All Command Options Explained

```bash
gh-chat-dataset [OPTIONS]
```

### Required Options
- `--repo URL` - The GitHub repository to convert (must be public or you need access)
- `--out DIRECTORY` - Where to save the dataset files

### Optional Fine-Tuning
- `--max-tokens 2048` - Skip samples longer than this (prevents memory issues)
- `--split-ratio 0.9` - How much data goes to training vs validation (0.9 = 90% train, 10% validation)
- `--allow-llm` - *(Experimental)* Use AI to generate labels where missing

### Real Examples
```bash
# Basic usage
gh-chat-dataset --repo https://github.com/user/repo.git --out ./my_dataset

# For larger models (more context)
gh-chat-dataset --repo https://github.com/user/repo.git --out ./my_dataset --max-tokens 4096

# More data for validation
gh-chat-dataset --repo https://github.com/user/repo.git --out ./my_dataset --split-ratio 0.8
```

## 📁 What Gets Extracted?

### From Python Files (.py)
- ✅ Functions with docstrings → "Write docstring" examples
- ✅ Classes with docstrings → "Document this class" examples
- ✅ Module docstrings → "Summarize this module" examples

### From JavaScript/TypeScript (.js, .jsx, .ts, .tsx)
- ✅ Functions with JSDoc comments → "Add JSDoc" examples
- ✅ Complex function signatures → Documentation examples

### From Markdown Files (.md)
- ✅ README sections → "Explain this concept" Q&A
- ✅ Documentation pages → Knowledge Q&A pairs
- ✅ API docs → Usage explanation examples

### What Gets Filtered Out
- ❌ Files without documentation (can't create good training pairs)
- ❌ Very short or very long samples (poor quality for training)
- ❌ Duplicate content (prevents overfitting)
- ❌ Generated files (node_modules, build outputs, etc.)

## 📈 Understanding Your Output

After running the tool, check `stats.json`:

```json
{
  "sha": "abc123...",           // Exact version of repo used
  "counts": {
    "total": 156,               // Total samples created
    "train": 140,               // Training samples (90%)
    "valid": 16                 // Validation samples (10%)
  }
}
```

**Good numbers to see:**
- 50+ total samples for small projects
- 500+ total samples for substantial codebases
- 1000+ total samples for large, well-documented projects

## 🎯 Perfect Repositories to Try

### Great for Beginners
- `pallets/itsdangerous` - Small, well-documented Python library
- `sindresorhus/is` - Simple JavaScript utilities with good docs
- `getsentry/sentry-python` - Medium-sized Python project

### For Larger Datasets
- `psf/requests` - Popular Python HTTP library
- `microsoft/TypeScript` - Large TypeScript codebase
- `django/django` - Web framework with extensive docs

### Best Results Come From
- ✅ Well-documented codebases
- ✅ Projects with consistent docstring/JSDoc style
- ✅ Repositories with good README files
- ✅ Active projects (recent commits)

## 🛠 Using Your Dataset with MLX

Once you have your dataset, here's how to use it for fine-tuning:

```python
# Load your dataset
import json

def load_dataset(path):
    with open(path, 'r') as f:
        return [json.loads(line) for line in f]

train_data = load_dataset('your_dataset/dataset.train.jsonl')
valid_data = load_dataset('your_dataset/dataset.valid.jsonl')

# Each sample has this format:
sample = train_data[0]
print(sample['messages'])  # The conversation
print(sample['meta'])      # Metadata about source
```

**Pro Tip**: The `messages` format is compatible with most modern fine-tuning frameworks including MLX, transformers, and OpenAI's fine-tuning API.

## 🔧 Troubleshooting

### "No samples extracted"
- ✅ Make sure the repo has documented code (docstrings, JSDoc, README)
- ✅ Try a well-known repo first (like `pallets/itsdangerous`)
- ✅ Check if the repo is public or you have access

### "Permission denied" errors
- ✅ Make sure you can access the repository
- ✅ For private repos, ensure your Git credentials are set up
- ✅ Try with a public repository first

### "Out of memory" errors
- ✅ Use `--max-tokens 1024` for smaller samples
- ✅ Try processing smaller repositories first
- ✅ Make sure you have sufficient disk space

### Dataset is too small
- ✅ Try repositories with more documentation
- ✅ Look for projects with consistent docstring styles
- ✅ Consider enabling `--allow-llm` for more samples (experimental)

## 🚀 Advanced Usage

### Batch Processing Multiple Repos
```bash
# Create a script to process multiple repositories
repos=(
  "https://github.com/user/repo1.git"
  "https://github.com/user/repo2.git"
  "https://github.com/user/repo3.git"
)

for repo in "${repos[@]}"; do
  name=$(basename "$repo" .git)
  gh-chat-dataset --repo "$repo" --out "./datasets/$name"
done
```

### Combining Datasets
```bash
# Merge multiple datasets
cat dataset1/dataset.train.jsonl dataset2/dataset.train.jsonl > combined_train.jsonl
cat dataset1/dataset.valid.jsonl dataset2/dataset.valid.jsonl > combined_valid.jsonl
```

## 👨‍💻 Contributing & Development

Want to improve the tool? Here's how to set up for development:

```bash
# Clone and setup
git clone https://github.com/ArjunDivecha/Repo2Dataset.git
cd Repo2Dataset

# Install in development mode
pip install -e .[dev]

# Run tests to make sure everything works
pytest

# Check code style
ruff check .

# Make your changes, then test
python -m pytest
```

### Adding New File Types
The tool is designed to be extensible. To add support for new languages:

1. Create a new extractor in `gh_chat_dataset/extract_xxx.py`
2. Add a builder function in `gh_chat_dataset/builders.py`
3. Update the file discovery patterns in `gh_chat_dataset/discover.py`
4. Add tests in `tests/`

## 📄 License

MIT License - feel free to use this for any project!

## 🙋‍♀️ Questions?

- 📖 Check the troubleshooting section above
- 🐛 Found a bug? [Open an issue](https://github.com/ArjunDivecha/Repo2Dataset/issues)
- 💡 Have an idea? [Start a discussion](https://github.com/ArjunDivecha/Repo2Dataset/discussions)

---

**Happy Training! 🤖✨**